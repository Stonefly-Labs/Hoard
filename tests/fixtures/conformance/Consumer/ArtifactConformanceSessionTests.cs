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
    [InlineData("local", ArtifactObservationPoint.StagePrefix)]
    [InlineData("local", ArtifactObservationPoint.BeforePublicationDecision)]
    [InlineData("local", ArtifactObservationPoint.CommitProgress)]
    [InlineData("object", ArtifactObservationPoint.StagePrefix)]
    [InlineData("object", ArtifactObservationPoint.BeforePublicationDecision)]
    [InlineData("object", ArtifactObservationPoint.CommitProgress)]
    public async Task Ordinary_cleanup_boundary_errors_cannot_borrow_intentional_failure_ownership(
        string provider, ArtifactObservationPoint point)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new IOException("InjectedCleanupFailure");
        Exception? disposalFailure = null;
        try
        {
            var bytes = "ordinary cleanup callback remains an error"u8.ToArray();
            if (point == ArtifactObservationPoint.CommitProgress)
            {
                using var control = new ArtifactPublicationAssertions.ShortSource(bytes);
                await ArtifactPublicationAssertions.PublishAsync(session.Store, control, new(1024), default);
            }
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource(bytes);
            if (point == ArtifactObservationPoint.StagePrefix)
            {
                await using var injection = await session.Faults.InjectObservationFailureAsync(point,
                    () => ValueTask.FromException(failure), default);
                Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                    await session.Store.StageAsync(ticket, source, new(), default));
            }
            else
            {
                var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                    await session.Store.StageAsync(ticket, source, new(), default)).Value;
                await using var injection = await session.Faults.InjectObservationFailureAsync(point,
                    () => ValueTask.FromException(failure), default);
                Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await session.Store.CommitAsync(staged, new(), default));
            }
            Assert.False(source.WasDisposed);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { disposalFailure = await Record.ExceptionAsync(() => session.DisposeAsync().AsTask()); }
        Assert.Equal("CleanupIncomplete", Assert.IsType<InvalidOperationException>(disposalFailure).Message);
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_failed_prefix_cleanup_and_stop_preserve_actual_ownership_and_fence_replay(string provider, bool stop)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var current = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, new(artifactBytes: 1024, stagingBytes: 1024)), context, default);
        IAsyncDisposable? restriction = null;
        IAsyncDisposable? observation = null;
        try
        {
            async ValueTask Arm() => observation = await current.Faults.InjectObservationFailureAsync(
                ArtifactObservationPoint.StagePrefix, async () => restriction =
                    await current.Faults.RestrictStorageCleanupAsync(ArtifactStorageArea.Staging, default), default);
            async ValueTask Restore()
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            var assertions = CleanupAssertions(current);
            if (stop)
            {
                var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                    await current.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
                using var source = new ArtifactPublicationAssertions.ShortSource("prefix retained through stop"u8.ToArray());
                await Arm();
                await assertions.FailedPrefixStopAsync(ticket, source,
                    options => current.Lifetime.StopAsync(options, default), Restore, default);
                if (provider == "local")
                {
                    ConformanceSessionOriginOutput.Write(output, current.CaptureOrigin());
                    current = Assert.IsType<ConformanceObservedArtifactSession>(await current.ReopenAsync(default));
                    await ArtifactCleanupAssertions.ReopenedAfterPrefixStopAsync(current.Store,
                        () => current.Faults.ObserveInitialization().Ready, ticket, default);
                }
            }
            else { await assertions.FailedPrefixAsync(Arm, Restore, default); }
            ConformanceSessionOriginOutput.Write(output, current.CaptureOrigin());
        }
        finally
        {
            try
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            finally { await current.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Theory]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_object_cleanup_and_stop_preserve_actual_selected_payload(string provider, bool stop)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, new(artifactBytes: 1024, stagingBytes: 1024)), context, default);
        IAsyncDisposable? restriction = null;
        IAsyncDisposable? observation = null;
        try
        {
            async ValueTask Restrict() => restriction =
                await session.Faults.RestrictStorageCleanupAsync(ArtifactStorageArea.Payloads, default);
            async ValueTask Observe()
            {
                observation = stop ? await session.Faults.InjectObservationFailureAsync(
                    ArtifactObservationPoint.BeforePublicationDecision, Restrict, default)
                    : await session.Faults.ObserveBoundaryAsync(ArtifactObservationPoint.DirectVerification, Restrict, default);
            }
            async ValueTask Remove()
            {
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            async ValueTask Restore()
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
            }
            if (stop)
            {
                await ArtifactRecoveryAssertions.RetainedObjectStopAsync(session.Store,
                    options => session.Lifetime.StopAsync(options, default),
                    token => StorageIdsAsync(session, ArtifactStorageArea.Payloads, token),
                    token => StorageIdsAsync(session, ArtifactStorageArea.Staging, token), Observe,
                    async () => { await Restore(); await Remove(); }, default);
            }
            else
            {
                await CleanupAssertions(session).ReusedObjectAsync(
                    token => StorageIdsAsync(session, ArtifactStorageArea.Payloads, token),
                    Observe, Remove, Restore, default);
            }
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Theory]
    [InlineData("object", ArtifactObservationPoint.CommitProgress, false)]
    [InlineData("object", ArtifactObservationPoint.BeforePublicationDecision, false)]
    [InlineData("object", ArtifactObservationPoint.CommitProgress, true)]
    [InlineData("object", ArtifactObservationPoint.BeforePublicationDecision, true)]
    public async Task Observed_unselected_object_cleanup_preserves_actual_residual_and_blocks_retry(
        string provider, ArtifactObservationPoint point, bool cancel)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        const int length = 512 * 1024;
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, new(artifactBytes: length, stagingBytes: length)), context, default);
        IAsyncDisposable? restriction = null;
        IAsyncDisposable? observation = null;
        try
        {
            async ValueTask Observe(CancellationTokenSource cancellation)
            {
                async ValueTask Restrict() => restriction =
                    await session.Faults.RestrictStorageCleanupAsync(ArtifactStorageArea.Payloads, default);
                observation = cancel ? await session.Faults.ObserveBoundaryAsync(point, async () =>
                {
                    await Restrict();
                    cancellation.Cancel();
                }, default) : await session.Faults.InjectObservationFailureAsync(point, Restrict, default);
            }
            async ValueTask Remove()
            {
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            async ValueTask Restore()
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
            }
            await CleanupAssertions(session).UnselectedObjectAsync(point == ArtifactObservationPoint.CommitProgress,
                token => StorageIdsAsync(session, ArtifactStorageArea.Payloads, token),
                async (id, token) => Assert.Single((await session.Faults.ObserveStorageAsync(token)).Payloads,
                    file => file.Id == id).Length,
                () => session.Faults.AwaitSettlementAsync(default).AsTask(),
                Observe, Remove, Restore, async () => { await Restore(); await Remove(); }, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try
            {
                if (restriction is not null) { await restriction.DisposeAsync(); }
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    private static ArtifactCleanupAssertions CleanupAssertions(IArtifactConformanceSession session) =>
        new(session.Store, session.Maintenance, session.Identity, () => session.Faults.ObserveInitialization().Ready,
            token => StorageIdsAsync(session, ArtifactStorageArea.Staging, token));

    private static async ValueTask<string[]> StorageIdsAsync(
        IArtifactConformanceSession session, ArtifactStorageArea area, CancellationToken cancellationToken)
    {
        var observed = await session.Faults.ObserveStorageAsync(cancellationToken);
        return (area == ArtifactStorageArea.Staging ? observed.Staging : observed.Payloads).Select(file => file.Id).ToArray();
    }

    [Theory]
    [InlineData("local", "overflow")]
    [InlineData("local", "directory")]
    [InlineData("local", "symlink")]
    [InlineData("object", "overflow")]
    [InlineData("object", "directory")]
    [InlineData("object", "symlink")]
    public async Task Observed_storage_inventory_bounds_all_actual_entries_and_rejects_nonfiles(string provider, string shape)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var root = Assert.Single(resources.Directories).DirectoryPath;
        var staging = Path.Combine(root, "store", provider == "local" ? "staging" : "multipart");
        var entries = new List<string>();
        var sentinel = Path.Combine(root, "owned-inventory-sentinel");
        await File.WriteAllBytesAsync(sentinel, [41]);
        try
        {
            try
            {
                if (shape == "symlink")
                {
                    var link = Path.Combine(staging, "unexpected-link");
                    File.CreateSymbolicLink(link, sentinel);
                    entries.Add(link);
                }
                else
                {
                    for (var index = 0; index < (shape == "overflow" ? 1025 : 1); index++)
                    {
                        var directory = Path.Combine(staging, "unexpected-" + index);
                        Directory.CreateDirectory(directory);
                        entries.Add(directory);
                    }
                }
                Assert.Equal(shape == "overflow" ? "FaultControl.Capacity" : "FaultControl.InvalidInput",
                    (await Assert.ThrowsAsync<InvalidOperationException>(
                        () => session.Faults.ObserveStorageAsync(default).AsTask())).Message);
            }
            finally
            {
                foreach (var entry in entries)
                {
                    if (shape == "symlink") { File.Delete(entry); }
                    else { Directory.Delete(entry); }
                }
            }
            var observed = await session.Faults.ObserveStorageAsync(default);
            Assert.Empty(observed.Staging);
            Assert.Empty(observed.Payloads);
            Assert.Equal(new byte[] { 41 }, await File.ReadAllBytesAsync(sentinel));
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Observed_committed_residual_cleanup_preserves_actual_receipt_and_owned_capacity(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, new(artifactBytes: 1024, stagingBytes: 1024)), context, default);
        IAsyncDisposable? restriction = null;
        try
        {
            async ValueTask<string[]> Staging(CancellationToken token) =>
                (await session.Faults.ObserveStorageAsync(token)).Staging.Select(file => file.Id).ToArray();
            var assertions = new ArtifactCleanupAssertions(session.Store, session.Maintenance, session.Identity,
                () => session.Faults.ObserveInitialization().Ready, Staging);
            async ValueTask Deny()
            {
                restriction = await session.Faults.RestrictStorageCleanupAsync(ArtifactStorageArea.Staging, default);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.RestrictStorageCleanupAsync(ArtifactStorageArea.Staging, default).AsTask())).Message);
            }
            ValueTask Restore() =>
                (restriction ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            await assertions.CommittedResidualAsync(Deny, Restore, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try { if (restriction is not null) { await restriction.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    public async Task Observed_failed_quarantine_persistence_retains_actual_ownership_through_retry_and_reopen(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var current = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        IAsyncDisposable? restriction = null;
        try
        {
            async ValueTask Damage(ArtifactStamp stamp, CancellationToken token)
            {
                await current.Faults.ArmAsync(ConformanceFault.PayloadDamage, token);
                try { await current.Faults.DamagePayloadAsync(stamp, truncate: true, token); }
                finally { await current.Faults.ReleaseAsync(ConformanceFault.PayloadDamage, default); }
            }
            async ValueTask Deny(CancellationToken token)
            {
                restriction = await current.Faults.RestrictRecordWritesAsync(token);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => current.Faults.RestrictRecordWritesAsync(token).AsTask())).Message);
            }
            ValueTask RestorePermissions() =>
                (restriction ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            async ValueTask<IArtifactStore> Reopen(CancellationToken token)
            {
                ConformanceSessionOriginOutput.Write(output, current.CaptureOrigin());
                current = Assert.IsType<ConformanceObservedArtifactSession>(await current.ReopenAsync(token));
                return current.Store;
            }
            await ArtifactEvidenceAssertions.FailedQuarantinePersistenceAsync(
                current.Store, current.Validator, current.Authority, current.Identity,
                current.Lifetime, () => current.Faults.ObserveInitialization().Ready, Damage,
                () =>
                {
                    if (OperatingSystem.IsWindows())
                    { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
                }, Deny, (stamp, bytes, token) => current.Faults.ReplacePayloadAsync(stamp, bytes, token),
                RestorePermissions, default, Reopen);
            ConformanceSessionOriginOutput.Write(output, current.CaptureOrigin());
        }
        finally
        {
            try { if (restriction is not null) { await restriction.DisposeAsync(); } }
            finally { await current.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("object")]
    public async Task Object_record_permissions_reject_without_borrowing_payload_access(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            Assert.Equal("FaultControl.Unsupported", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => session.Faults.RestrictRecordWritesAsync(default).AsTask())).Message);
            using var source = new ArtifactPublicationAssertions.ShortSource("unsupported record permissions leave actual payload usable"u8.ToArray());
            var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1024), default);
            await using (var access = await session.Faults.RestrictPayloadAccessAsync(receipt.Stamp, unavailable: true, default)) { }
            Assert.Equal("unsupported record permissions leave actual payload usable"u8.ToArray(),
                await ArtifactPublicationAssertions.ReadAsync(session.Store, receipt.Stamp, default));
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_access_scope_protects_actual_incarnation_until_restoration(string provider, bool unavailable)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        IAsyncDisposable? access = null;
        try
        {
            using var source = new ArtifactPublicationAssertions.ShortSource("access restoration must precede physical reclamation"u8.ToArray());
            var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1024), default);
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default)).Value;
            access = await session.Faults.RestrictPayloadAccessAsync(receipt.Stamp, unavailable, default);
            var deleting = session.Store.DeleteAsync(ticket, new(), default).AsTask();
            try
            {
                using var budget = new CancellationTokenSource(context.ControlBudget);
                while (session.Faults.WaitingAuthorityAdmissions == 0) { await Task.Delay(1, budget.Token); }
                Assert.False(deleting.IsCompleted);
            }
            finally { await access.DisposeAsync(); }
            Assert.Equal(ArtifactReclamation.Reclaimed, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
                await deleting).Value.Reclamation);
            Assert.Equal(ArtifactFailureCode.NotFound, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await session.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try { if (access is not null) { await access.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Ordinary_access_release_errors_restore_actual_payload_before_faulted_settlement(
        string provider, bool unavailable) =>
        await AccessReleaseErrorAsync(provider, unavailable, new IOException("Ordinary access release failure"));

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Ordinary_access_release_cancellation_restores_actual_payload_before_faulted_settlement(
        string provider, bool unavailable) =>
        await AccessReleaseErrorAsync(provider, unavailable, new OperationCanceledException("Ordinary access release cancellation"));

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    public async Task Ordinary_record_permission_release_errors_restore_actual_mode_before_faulted_settlement(
        string provider, bool cancellation) =>
        await AccessReleaseErrorAsync(provider, false,
            cancellation ? new OperationCanceledException("Ordinary record access cancellation")
                : new IOException("Ordinary record access failure"), recordWrites: true);

    private async Task AccessReleaseErrorAsync(string provider, bool unavailable, Exception failure, bool recordWrites = false)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var bytes = "payload access restoration after a release observer exception"u8.ToArray();
        IAsyncDisposable? observation = null;
        IAsyncDisposable? access = null;
        string? recordDirectory = null;
        UnixFileMode? originalMode = null;
        Exception? disposalFailure = null;
        try
        {
            using var source = new ArtifactPublicationAssertions.ShortSource(bytes);
            var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1024), default);
            if (recordWrites)
            {
                if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
                recordDirectory = Assert.Single(Directory.GetDirectories(
                    Assert.Single(resources.Directories).DirectoryPath, "decisions", SearchOption.AllDirectories));
                originalMode = File.GetUnixFileMode(recordDirectory);
            }
            ValueTask<IAsyncDisposable> Restrict() => recordWrites
                ? session.Faults.RestrictRecordWritesAsync(default)
                : session.Faults.RestrictPayloadAccessAsync(receipt.Stamp, unavailable, default);
            observation = await session.Faults.ObserveBoundaryAsync(ArtifactObservationPoint.OperationReleased,
                () => ValueTask.FromException(failure), default);
            if (failure is OperationCanceledException)
            { access = await Restrict(); }
            else
            {
                Assert.Same(failure, await Record.ExceptionAsync(() => Restrict().AsTask()));
            }
            await observation.DisposeAsync();
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            if (observation is not null) { await observation.DisposeAsync(); }
            disposalFailure = await Record.ExceptionAsync(() => session.DisposeAsync().AsTask());
            if (access is not null) { await access.DisposeAsync(); }
        }
        Assert.Equal("CleanupIncomplete", Assert.IsType<InvalidOperationException>(disposalFailure).Message);
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        var root = Assert.Single(resources.Directories).DirectoryPath;
        Assert.Empty(Directory.GetDirectories(root, "*-qualification-offline", SearchOption.AllDirectories));
        var payload = Assert.Single(Directory.GetFiles(root, "*", SearchOption.AllDirectories),
            path => new FileInfo(path).Length == bytes.Length);
        Assert.Equal(bytes, await File.ReadAllBytesAsync(payload));
        if (recordDirectory is not null)
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
            Assert.Equal(originalMode, File.GetUnixFileMode(recordDirectory));
        }
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_access_application_joins_actual_shutdown_before_releasing_owned_resources(
        string provider, bool unavailable) => await AccessApplicationShutdownAsync(provider, unavailable);

    [Theory]
    [InlineData("local")]
    public async Task Observed_record_permission_application_joins_actual_shutdown_before_resource_settlement(string provider) =>
        await AccessApplicationShutdownAsync(provider, false, recordWrites: true);

    private async Task AccessApplicationShutdownAsync(string provider, bool unavailable, bool recordWrites = false)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var released = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        IAsyncDisposable? observation = null;
        try
        {
            using var source = new ArtifactPublicationAssertions.ShortSource("access scope remains genuine owned work"u8.ToArray());
            var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1024), default);
            var origin = session.CaptureOrigin();
            observation = await session.Faults.ObserveBoundaryAsync(
                recordWrites ? ArtifactObservationPoint.OperationCompleted : ArtifactObservationPoint.PayloadSelected,
                () =>
                {
                    entered.TrySetResult();
                    return new(released.Task.WaitAsync(context.BarrierBudget));
                }, default);
            var applying = (recordWrites ? session.Faults.RestrictRecordWritesAsync(default)
                : session.Faults.RestrictPayloadAccessAsync(receipt.Stamp, unavailable, default)).AsTask();
            await entered.Task.WaitAsync(context.ControlBudget);
            var disposing = session.DisposeAsync().AsTask();
            try
            {
                await resources.Observing.Task.WaitAsync(context.ControlBudget);
                Assert.False(disposing.IsCompleted);
                Assert.False(Assert.Single(resources.Settlements).Value.IsCompleted);
            }
            finally { released.TrySetResult(); }
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(() => applying)).Message);
            await disposing;
            ConformanceSessionOriginOutput.Write(output, origin);
        }
        finally
        {
            released.TrySetResult();
            try { if (observation is not null) { await observation.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_validation_access_failures_preserve_actual_intact_content(string provider, bool unavailable)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        IAsyncDisposable? access = null;
        try
        {
            async ValueTask Deny(ArtifactStamp stamp, CancellationToken token)
            {
                var stale = new ArtifactStamp(stamp.Store, stamp.Identity, Guid.NewGuid());
                Assert.Equal("FaultControl.Conflict", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.RestrictPayloadAccessAsync(stale, unavailable, token).AsTask())).Message);
                access = await session.Faults.RestrictPayloadAccessAsync(stamp, unavailable, token);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.RestrictPayloadAccessAsync(stamp, unavailable, token).AsTask())).Message);
            }
            async ValueTask Restore()
            {
                if (access is not null) { await access.DisposeAsync(); }
            }
            await ArtifactEvidenceAssertions.ValidationAccessFailureAsync(
                session.Store, session.Validator, session.Authority, session.Identity, unavailable,
                () =>
                {
                    if (OperatingSystem.IsWindows())
                    { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
                }, Deny, Restore, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            try { if (access is not null) { await access.DisposeAsync(); } }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("object")]
    public async Task Object_record_write_fault_rejects_without_borrowing_actual_deletion(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        try
        {
            Assert.Equal("FaultControl.Unsupported", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => session.Faults.InjectRecordWriteFailureAsync(3, () => { }, default).AsTask())).Message);
            using var source = new ArtifactPublicationAssertions.ShortSource("physical deletion stays independently held"u8.ToArray());
            var receipt = await ArtifactPublicationAssertions.PublishAsync(session.Store, source, new(1024), default);
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default)).Value;
            await session.Faults.ArmAsync(ConformanceFault.NativeNonCooperation, default);
            var deleting = session.Store.DeleteAsync(ticket, new(), default).AsTask();
            try
            {
                await session.Faults.WaitForBoundaryAsync(ConformanceFault.NativeNonCooperation, default);
                Assert.False(deleting.IsCompleted);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.InjectRecordWriteFailureAsync(3, () => { }, default).AsTask())).Message);
            }
            finally { await session.Faults.ReleaseAsync(ConformanceFault.NativeNonCooperation, default); }
            Assert.Equal(ArtifactReclamation.Reclaimed, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
                await deleting).Value.Reclamation);
            Assert.Equal("FaultControl.Unsupported", (await Assert.ThrowsAsync<InvalidOperationException>(
                () => session.Faults.InjectRecordWriteFailureAsync(3, () => { }, default).AsTask())).Message);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "committed-decision")]
    [InlineData("local", "durable-receipt")]
    public async Task Observed_local_durable_reopen_preserves_retired_decisions_and_receipt_release(
        string provider, string consumer)
    {
        await using var resources = new RecordingDirectories();
        var clock = new ControlledClock();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", clock,
            resources, new ConformanceEvidenceBuffer());
        var limits = consumer == "committed-decision"
            ? new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024, liveTickets: 1, committedIdentities: 1)
            : new ArtifactLimits(artifactBytes: 1024, stagingBytes: 1024);
        IArtifactConformanceSession current = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, limits, admissionProbe: ArtifactAdmissionProbe.Complete), context, default);
        var origins = new List<ConformanceSessionOrigin>
        {
            Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin()
        };
        IArtifactFaultRegistration? recordFailure = null;
        var cleanupAllowed = true;
        try
        {
            async ValueTask<(IArtifactStore Store, IArtifactStoreLifetime Lifetime)> Reopen(CancellationToken token)
            {
                current = await current.ReopenAsync(token);
                origins.Add(Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin());
                return (current.Store, current.Lifetime);
            }
            async ValueTask InjectRecordFailure(int occurrence)
            {
                recordFailure = await current.Faults.InjectRecordWriteFailureAsync(
                    occurrence, () => { }, default);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => current.Faults.InjectRecordWriteFailureAsync(occurrence, () => { }, default).AsTask())).Message);
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => current.Faults.ArmAsync(ConformanceFault.NativeNonCooperation, default).AsTask())).Message);
            }
            ValueTask RemoveRecordFailure() =>
                (recordFailure ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            if (consumer == "committed-decision")
            {
                await ArtifactRecoveryAssertions.CommittedDecisionRollbackAsync(
                    current.Store, current.Lifetime, current.Identity, current.Authority, limits,
                    clock.SetUtc, clock.Advance, Reopen, value => cleanupAllowed = value, () => cleanupAllowed, default);
            }
            else
            {
                await ArtifactRecoveryAssertions.DurableReceiptReleaseAsync(
                    current.Store, current.Lifetime, current.Identity, current.Authority, limits,
                    InjectRecordFailure, RemoveRecordFailure, Reopen, default);
                Assert.Equal(3, (recordFailure ?? throw new InvalidOperationException("BindingInvalid")).ObservationCount);
            }
            foreach (var origin in origins) { ConformanceSessionOriginOutput.Write(output, origin); }
        }
        finally
        {
            try { if (recordFailure is not null) { await recordFailure.DisposeAsync(); } }
            finally { await current.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    public async Task Ordinary_record_write_callback_errors_still_fault_actual_settlement(string provider)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var failure = new IOException("Interrupted reservation release.");
        Exception? disposalFailure = null;
        try
        {
            await session.Faults.ArmAsync(ConformanceFault.NativeNonCooperation, default);
            try
            {
                Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<InvalidOperationException>(
                    () => session.Faults.InjectRecordWriteFailureAsync(3, () => { }, default).AsTask())).Message);
            }
            finally { await session.Faults.ReleaseAsync(ConformanceFault.NativeNonCooperation, default); }
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("ordinary record callback ownership"u8.ToArray());
            var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                await session.Store.StageAsync(ticket, source, new(), default)).Value;
            await using var injection = await session.Faults.InjectRecordWriteFailureAsync(3, () => throw failure, default);
            Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await session.Store.CommitAsync(staged, new(), default)).Code);
            Assert.Equal(3, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { disposalFailure = await Record.ExceptionAsync(() => session.DisposeAsync().AsTask()); }
        Assert.Equal("CleanupIncomplete", Assert.IsType<InvalidOperationException>(disposalFailure).Message);
        var settlement = Assert.Single(resources.Settlements).Value;
        Assert.True(settlement.IsFaulted);
        Assert.Contains(failure, settlement.Exception!.InnerExceptions);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    public async Task Observed_local_reconciliation_cannot_finalize_after_actual_read_quarantine(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var reading = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var verifying = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseRead = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseReconciliation = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var observations = new List<IAsyncDisposable>();
        IAsyncDisposable? loss = null;
        ArtifactStamp? stamp = null;
        try
        {
            async ValueTask LoseAcknowledgment() => loss =
                await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
            ValueTask RestoreAcknowledgment() =>
                (loss ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            async ValueTask Damage(ArtifactStagedWrite staged, CancellationToken token)
            {
                stamp = await ObservePublicationStampAsync(session, staged, token);
                await session.Faults.ArmAsync(ConformanceFault.PayloadDamage, token);
                try
                {
                    await session.Faults.DamagePayloadAsync(stamp, truncate: false, token);
                    await session.Faults.WaitForBoundaryAsync(ConformanceFault.PayloadDamage, token);
                }
                finally { await session.Faults.ReleaseAsync(ConformanceFault.PayloadDamage, default); }
            }
            async ValueTask ObserveCopy() => observations.Add(await session.Faults.ObserveBoundaryAsync(
                ArtifactObservationPoint.ReadCopy, () =>
                {
                    reading.TrySetResult();
                    return new(releaseRead.Task.WaitAsync(context.BarrierBudget));
                }, default));
            async ValueTask ObserveReconciliation() => observations.Add(await session.Faults.ObserveBoundaryAsync(
                ArtifactObservationPoint.ReconciliationVerified, () =>
                {
                    verifying.TrySetResult();
                    return new(releaseReconciliation.Task.WaitAsync(context.BarrierBudget));
                }, default));
            ValueTask Restore(ArtifactStagedWrite staged, ReadOnlyMemory<byte> bytes, CancellationToken token) =>
                session.Faults.ReplacePayloadAsync(stamp ?? throw new InvalidOperationException("BindingInvalid"), bytes, token);
            await ArtifactReadAssertions.ReconciliationQuarantineRaceAsync(session.Store,
                LoseAcknowledgment, RestoreAcknowledgment, Damage, ObserveCopy, ObserveReconciliation,
                token => reading.Task.WaitAsync(context.ControlBudget, token),
                token => verifying.Task.WaitAsync(context.ControlBudget, token),
                () => releaseRead.TrySetResult(), () => releaseReconciliation.TrySetResult(), Restore, default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            releaseRead.TrySetResult();
            releaseReconciliation.TrySetResult();
            try
            {
                await session.Faults.AwaitSettlementAsync(default);
                if (loss is not null) { await loss.DisposeAsync(); }
                foreach (var observation in observations) { await observation.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "open")]
    [InlineData("local", "publication")]
    [InlineData("local", "reconciliation")]
    [InlineData("object", "open")]
    [InlineData("object", "publication")]
    [InlineData("object", "reconciliation")]
    public async Task Observed_committed_detection_paths_quarantine_actual_restored_bytes(string provider, string detection)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        IArtifactConformanceSession current = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider), context, default);
        var origins = new List<ConformanceSessionOrigin>
        {
            Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin()
        };
        IAsyncDisposable? publication = null;
        ArtifactStamp? stamp = null;
        try
        {
            async ValueTask Damage(ArtifactStagedWrite staged, bool truncate, CancellationToken token)
            {
                stamp = await ObservePublicationStampAsync(current, staged, token);
                await current.Faults.ArmAsync(ConformanceFault.PayloadDamage, token);
                try
                {
                    await current.Faults.DamagePayloadAsync(stamp, truncate, token);
                    await current.Faults.WaitForBoundaryAsync(ConformanceFault.PayloadDamage, token);
                }
                finally { await current.Faults.ReleaseAsync(ConformanceFault.PayloadDamage, default); }
            }
            async ValueTask ObservePublication(ArtifactStagedWrite staged) =>
                publication = detection == "reconciliation"
                    ? await current.Faults.InjectPublicationAcknowledgmentLossAsync(default)
                    : await current.Faults.ObserveBoundaryAsync(ArtifactObservationPoint.PublicationSelected,
                        () => Damage(staged, truncate: true, default), default);
            ValueTask RemovePublication() =>
                (publication ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            ValueTask Restore(ArtifactStagedWrite staged, ReadOnlyMemory<byte> bytes, CancellationToken token) =>
                current.Faults.ReplacePayloadAsync(stamp ?? throw new InvalidOperationException("BindingInvalid"), bytes, token);
            async ValueTask<IArtifactStore> Reopen(CancellationToken token)
            {
                current = await current.ReopenAsync(token);
                origins.Add(Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin());
                return current.Store;
            }
            await ArtifactReadAssertions.CommittedDetectionQuarantineAsync(current.Store, detection,
                provider == "local" ? ArtifactDurability.LocalProcessCrash : ArtifactDurability.SimulationOnly,
                current.Faults.RemovePayloadAsync, current.Faults.ReplacePayloadAsync,
                ObservePublication, RemovePublication, (staged, token) => Damage(staged, truncate: false, token),
                Restore, default, null, provider == "local" ? Reopen : null);
            foreach (var origin in origins) { ConformanceSessionOriginOutput.Write(output, origin); }
        }
        finally
        {
            try
            {
                await current.Faults.AwaitSettlementAsync(default);
                if (publication is not null) { await publication.DisposeAsync(); }
            }
            finally { await current.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", ArtifactAdmissionProbe.Complete)]
    [InlineData("local", ArtifactAdmissionProbe.Version)]
    [InlineData("local", ArtifactAdmissionProbe.Publication)]
    [InlineData("local", ArtifactAdmissionProbe.Deletion)]
    [InlineData("local", ArtifactAdmissionProbe.Recovery)]
    [InlineData("local", ArtifactAdmissionProbe.Fencing)]
    [InlineData("local", ArtifactAdmissionProbe.Readers)]
    [InlineData("local", ArtifactAdmissionProbe.Streaming)]
    [InlineData("local", ArtifactAdmissionProbe.ForeignAuthority)]
    [InlineData("object", ArtifactAdmissionProbe.Complete)]
    [InlineData("object", ArtifactAdmissionProbe.Version)]
    [InlineData("object", ArtifactAdmissionProbe.Publication)]
    [InlineData("object", ArtifactAdmissionProbe.Deletion)]
    [InlineData("object", ArtifactAdmissionProbe.Recovery)]
    [InlineData("object", ArtifactAdmissionProbe.Fencing)]
    [InlineData("object", ArtifactAdmissionProbe.Readers)]
    [InlineData("object", ArtifactAdmissionProbe.Streaming)]
    [InlineData("object", ArtifactAdmissionProbe.ForeignAuthority)]
    public async Task Observed_initial_admission_preserves_actual_capabilities_and_no_io_rejection(
        string provider, ArtifactAdmissionProbe probe)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var limits = probe == ArtifactAdmissionProbe.Complete
            ? new ArtifactLimits(artifactBytes: 1024, stagingBytes: 2048, transferSlots: 1, waitingCalls: 0)
            : new ArtifactLimits();
        var session = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider, limits, admissionProbe: probe), context, default);
        try
        {
            if (probe == ArtifactAdmissionProbe.Complete)
            {
                await ArtifactCapabilityAssertions.CompleteProfileAsync(
                    session.Lifetime, session.Identity, session.Authority,
                    () => session.Faults.ObserveInitialization().Ready, default);
            }
            else
            {
                var gap = probe == ArtifactAdmissionProbe.ForeignAuthority
                    ? "authority" : probe.ToString().ToLowerInvariant();
                await ArtifactCapabilityAssertions.MissingGuaranteeAsync(session.Lifetime,
                    new(ArtifactInitializationMode.CreateEmpty, session.Identity, session.Authority), gap,
                    () => session.Faults.ObserveInitialization().RootExists,
                    () => session.Faults.ObserveInitialization().Ready, default);
            }
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { await session.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Observed_validation_first_quarantine_survives_actual_restoration_and_reopen(
        string provider, bool missing)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        IArtifactConformanceSession current = await ConformanceObservedArtifactSession.OpenAsync(
            Binding(provider), context, default);
        var origins = new List<ConformanceSessionOrigin>
        {
            Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin()
        };
        try
        {
            async ValueTask Damage(ArtifactStamp stamp, CancellationToken token)
            {
                if (missing) { await current.Faults.RemovePayloadAsync(stamp, token); }
                else
                {
                    await current.Faults.ArmAsync(ConformanceFault.PayloadDamage, token);
                    try
                    {
                        await current.Faults.DamagePayloadAsync(stamp, truncate: true, token);
                        await current.Faults.WaitForBoundaryAsync(ConformanceFault.PayloadDamage, token);
                    }
                    finally { await current.Faults.ReleaseAsync(ConformanceFault.PayloadDamage, default); }
                }
            }
            await ArtifactEvidenceAssertions.ValidationFirstCorruptionAsync(
                current.Store, current.Validator, current.Authority, current.Identity,
                Damage, current.Faults.ReplacePayloadAsync, default, null,
                provider == "local" ? async token =>
                {
                    current = await current.ReopenAsync(token);
                    var reopened = Assert.IsType<ConformanceObservedArtifactSession>(current).CaptureOrigin();
                    Assert.Equal(origins[0].SessionId, reopened.ParentSessionId);
                    origins.Add(reopened);
                    return current.Store;
                }
            : null);
            foreach (var origin in origins) { ConformanceSessionOriginOutput.Write(output, origin); }
        }
        finally { await current.DisposeAsync(); }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Observed_admitted_open_rechecks_actual_quarantine_before_result_handoff(string provider)
    {
        await using var resources = new RecordingDirectories();
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var released = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        IAsyncDisposable? observation = null;
        try
        {
            async ValueTask Observe() => observation = await session.Faults.ObserveBoundaryAsync(
                provider == "local" ? ArtifactObservationPoint.ReadOpened : ArtifactObservationPoint.DirectVerification,
                () =>
                {
                    entered.TrySetResult();
                    return new(released.Task.WaitAsync(context.BarrierBudget));
                }, default);
            ValueTask Remove() => (observation ?? throw new InvalidOperationException("BindingInvalid")).DisposeAsync();
            await ArtifactReadAssertions.AdmittedOpenRechecksQuarantineAsync(
                session.Store, session.Validator, session.Authority, session.Identity,
                Observe, token => entered.Task.WaitAsync(context.ControlBudget, token), Remove,
                session.Faults.ReplacePayloadAsync, () => released.TrySetResult(), default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally
        {
            released.TrySetResult();
            try
            {
                await session.Faults.AwaitSettlementAsync(default);
                if (observation is not null) { await observation.DisposeAsync(); }
            }
            finally { await session.DisposeAsync(); }
        }
        Assert.True(Assert.Single(resources.Settlements).Value.IsCompletedSuccessfully);
        Assert.DoesNotContain(resources.Observations, item => item.State == ConformanceOwnershipState.Released);
    }

    [Theory]
    [InlineData("local", "receipt")]
    [InlineData("object", "receipt")]
    [InlineData("local", "read-open")]
    [InlineData("object", "read-open")]
    [InlineData("local", "verified-reconciliation")]
    [InlineData("object", "verified-reconciliation")]
    [InlineData("local", "pending-reclamation")]
    [InlineData("object", "pending-reclamation")]
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
            async ValueTask LoseDeletionAcknowledgment() => registrations.Add(ArtifactObservationPoint.DeleteRemoved,
                await session.Faults.InjectObservationFailureAsync(
                    ArtifactObservationPoint.DeleteRemoved, () => ValueTask.CompletedTask, default));
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
                "pending-reclamation" => ArtifactDeletionAssertions.PendingReclamationAsync(
                    session.Store, session.Maintenance, session.Identity, LoseDeletionAcknowledgment, default),
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
    [InlineData("local", ArtifactObservationPoint.DeleteRemoved)]
    [InlineData("object", ArtifactObservationPoint.DeleteRemoved)]
    public async Task Ordinary_errors_inside_owned_failure_callbacks_still_fault_actual_settlement(
        string provider, ArtifactObservationPoint point)
    {
        await using var resources = new RecordingDirectories(allowFailedSettlement: true);
        var context = new ConformanceRunContext(RunId(), "full-artifact-binding", TimeProvider.System,
            resources, new ConformanceEvidenceBuffer());
        var session = await ConformanceObservedArtifactSession.OpenAsync(Binding(provider), context, default);
        Exception failure = point == ArtifactObservationPoint.DeleteRemoved
            ? new IOException("InjectedDeleteAcknowledgmentLoss")
            : new InvalidOperationException("InjectedObservationFailure");
        Exception? disposalFailure = null;
        try
        {
            var ticket = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                await session.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Value;
            using var source = new ArtifactPublicationAssertions.ShortSource("ordinary callback ownership"u8.ToArray());
            var staged = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Success>(
                await session.Store.StageAsync(ticket, source, new(), default)).Value;
            ArtifactMutationReceipt? committed = null;
            if (point == ArtifactObservationPoint.ReconciliationVerified)
            {
                await using var loss = await session.Faults.InjectPublicationAcknowledgmentLossAsync(default);
                Assert.Equal(ArtifactFailureCode.Uncertain, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await session.Store.CommitAsync(staged, new(), default)).Code);
            }
            else
            {
                committed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Success>(
                await session.Store.CommitAsync(staged, new(), default)).Value;
            }
            await using var injection = await session.Faults.InjectObservationFailureAsync(
                point, () => ValueTask.FromException(failure), default);
            if (point == ArtifactObservationPoint.ReadOpened)
            {
                Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                    await session.Store.OpenReadAsync(new(staged.Identity.Digest), new(), default)).Code);
            }
            else if (point == ArtifactObservationPoint.ReconciliationVerified)
            {
                Assert.Equal(ArtifactFailureCode.InternalFailure, Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await session.Store.ReconcileAsync(ticket, new(), default)).Code);
            }
            else
            {
                Assert.NotNull(committed);
                var deletion = Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Success>(
                    await session.Store.ReserveDeleteAsync(new(committed.Stamp), new(), default)).Value;
                Assert.Equal(ArtifactFailureCode.Uncertain,
                    Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                        await session.Store.DeleteAsync(deletion, new(), default)).Code);
                await injection.DisposeAsync();
                var cleanup = Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Success>(
                    await session.Maintenance.CleanupAsync(new(session.Identity,
                        [new ArtifactCleanupTarget.RemovedIncarnation(committed.Stamp)]), new(), default)).Value;
                Assert.Equal(1, cleanup.Completed);
            }
            Assert.Equal(1, injection.ObservationCount);
            await session.Faults.AwaitSettlementAsync(default);
            ConformanceSessionOriginOutput.Write(output, session.CaptureOrigin());
        }
        finally { disposalFailure = await Record.ExceptionAsync(() => session.DisposeAsync().AsTask()); }
        Assert.Equal("CleanupIncomplete", Assert.IsType<InvalidOperationException>(disposalFailure).Message);
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

    private static async ValueTask<ArtifactStamp> ObservePublicationStampAsync(
        IArtifactConformanceSession session, ArtifactStagedWrite staged, CancellationToken cancellationToken)
    {
        var page = Assert.IsType<ArtifactResult<ArtifactRecoveryPage>.Success>(
            await session.Maintenance.ObserveAsync(new(session.Identity, ArtifactRecoveryKind.Committed),
                new(), cancellationToken)).Value;
        Assert.IsType<ArtifactOption<string>.None>(page.Continuation);
        var selected = Assert.Single(page.Observations);
        Assert.Equal(staged.Owner.Ticket.Id, selected.OperationId);
        var stamp = Assert.IsType<ArtifactOption<ArtifactStamp>.Some>(selected.Stamp).Value;
        Assert.Equal(session.Identity, stamp.Store);
        Assert.Equal(staged.Identity, stamp.Identity);
        return stamp;
    }

    private static Guid RunId()
    {
        if (!Guid.TryParseExact(Environment.GetEnvironmentVariable("HOARD_ORIGIN_RUN_ID"), "D", out var runId)
            || runId == Guid.Empty)
        { throw new InvalidOperationException("PrerequisiteMissing"); }
        return runId;
    }

    private static IArtifactConformanceBinding Binding(string provider, ArtifactLimits? limits = null,
        Func<ArtifactStamp, CancellationToken, ValueTask<ArtifactReferenceObservation>>? references = null,
        ArtifactAdmissionProbe admissionProbe = ArtifactAdmissionProbe.None)
    {
        var variable = provider switch
        {
            "local" => "HOARD_ARTIFACT_LOCAL_PACKAGE_SHA256",
            "object" => "HOARD_ARTIFACT_OBJECT_PACKAGE_SHA256",
            _ => throw new ArgumentException("BindingInvalid")
        };
        var sha256 = Environment.GetEnvironmentVariable(variable)
            ?? throw new InvalidOperationException("PrerequisiteMissing");
        var options = new ArtifactAssertionOptions(admissionProbe, limits, references: references ?? ((_, _) =>
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
