using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.Local;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactFailureTests
{
    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024));
        using var original = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var committed = await PublishAsync(driver, original, new(1024));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var duplicate = new ShortSource("committed bytes survive residual cleanup"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, duplicate, new(), default));
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix staging proof required."); }
        File.SetUnixFileMode(driver.StagingDirectory, UnixFileMode.UserRead | UnixFileMode.UserExecute);
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), default));
            Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(driver.Ready);
            var receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
            Assert.Equal(committed.Stamp, receipt.Stamp);
            var page = Success(await driver.Maintenance.ObserveAsync(
                new(driver.Identity, ArtifactRecoveryKind.Staging), new(), default));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            Assert.Equal(ArtifactFailureCode.AccessDenied, Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                await driver.Maintenance.CleanupAsync(request, new(), default)).Code);
            RestorePrefixCleanup(driver);
            Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(request, new(), default)).Completed);
            Assert.True(driver.Ready);
            Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
            Assert.Equal(receipt, Success(await driver.Store.CommitAsync(staged, new(), default)));
            Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt);
            Assert.Equal("committed bytes survive residual cleanup"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
            Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            Assert.False(duplicate.WasDisposed);
        }
        finally { RestorePrefixCleanup(driver); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new(artifactBytes: 1024, stagingBytes: 1024));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("unreclaimed failed prefix"u8.ToArray());
        DenyPrefixCleanup(driver);
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await driver.Store.StageAsync(ticket, source, new(), default));
            Assert.Equal(ArtifactFailureCode.AccessDenied, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(driver.Ready);
            Assert.False(source.WasDisposed);
            Assert.True(source.BytesRead > 0);
            Assert.Single(Directory.GetFiles(driver.StagingDirectory));
            Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default)).Code);
            var page = Success(await driver.Maintenance.ObserveAsync(
                new(driver.Identity, ArtifactRecoveryKind.Staging), new(), default));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var retry = Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                    await driver.Maintenance.CleanupAsync(request, new(), default));
                Assert.Equal(ArtifactFailureCode.AccessDenied, retry.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, retry.Cleanup);
                Assert.False(driver.Ready);
            }
            RestorePrefixCleanup(driver);
            var reclaimed = Success(await driver.Maintenance.CleanupAsync(request, new(), default));
            Assert.Equal(1, reclaimed.Completed);
            Assert.True(reclaimed.ReclaimedBytes > 0);
            Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
            Assert.True(driver.Ready);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
            using var replay = new ShortSource([1]);
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await driver.Store.StageAsync(ticket, replay, new(), default));
            Assert.Equal(0, replay.BytesRead);
            var fresh = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var replacement = new ShortSource("fresh owner after reclamation"u8.ToArray());
            var staged = Success(await driver.Store.StageAsync(fresh, replacement, new(), default));
            Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(request, new(), default)).Conflicted);
            Assert.IsType<ArtifactResult<ArtifactStagingOwner>.Failure>(await driver.Store.RenewAsync(owner, new(), default));
            Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(await driver.Store.AbandonAsync(owner, new(), default));
            var receipt = Success(await driver.Store.CommitAsync(staged, new(), default));
            Assert.Equal("fresh owner after reclamation"u8.ToArray(), await ReadAsync(driver, receipt.Stamp));
        }
        finally { RestorePrefixCleanup(driver); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Stop_retains_failed_prefix_ownership_until_reclamation_can_settle(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("prefix retained through stop"u8.ToArray());
        DenyPrefixCleanup(driver);
        try
        {
            Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await driver.Store.StageAsync(ticket, source, new(), default));
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var failed = Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(await driver.StopAsync(new()));
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, failed.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
                Assert.Single(Directory.GetFiles(driver.StagingDirectory));
                Assert.False(source.WasDisposed);
            }
        }
        finally { RestorePrefixCleanup(driver); }
        Assert.Equal(ArtifactCleanupState.Released, Success(await driver.StopAsync(new())).State);
        Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
        if (provider == "local")
        {
            var reopened = new LocalArtifactStore(Path.GetDirectoryName(driver.StagingDirectory)!);
            Success(await reopened.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, driver.Identity,
                driver.Authority, new(artifactBytes: 1024, stagingBytes: 1024)), new(), default));
            try
            {
                Assert.True(reopened.Ready);
                Assert.IsType<ArtifactResolution.NotCommitted>(Success(await reopened.ReconcileAsync(ticket, new(), default)));
                Success(await reopened.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
                using var replay = new ShortSource([1]);
                Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(await reopened.StageAsync(ticket, replay, new(), default));
                Assert.Equal(0, replay.BytesRead);
            }
            finally { Success(await reopened.StopAsync(new(), default)); }
        }
    }

    private static void DenyPrefixCleanup(ArtifactProviderDriver driver)
    {
        ValueTask FailAfterPrefix()
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix staging proof required."); }
            File.SetUnixFileMode(driver.StagingDirectory, UnixFileMode.UserRead | UnixFileMode.UserExecute);
            return ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        }
        if (driver.LocalControls is { } local) { local.SetObserver("stage.prefix", FailAfterPrefix); }
        else { driver.ObjectControls!.SetObserver("multipart.part", FailAfterPrefix); }
    }

    private static void RestorePrefixCleanup(ArtifactProviderDriver driver)
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix staging proof required."); }
        File.SetUnixFileMode(driver.StagingDirectory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        if (driver.LocalControls is { } local) { local.RemoveObserver("stage.prefix"); }
        else { driver.ObjectControls!.RemoveObserver("multipart.part"); }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Storage_failures_remain_distinct_and_sanitized_and_do_not_publish_partial_content(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        (Exception Error, ArtifactFailureCode Code)[] failures =
        [
            (new UnauthorizedAccessException(ArtifactTestData.Canary), ArtifactFailureCode.AccessDenied),
            (new IOException(ArtifactTestData.Canary, 28), ArtifactFailureCode.Capacity),
            (new IOException(ArtifactTestData.Canary), ArtifactFailureCode.Unavailable),
            (new InvalidOperationException(ArtifactTestData.Canary), ArtifactFailureCode.InternalFailure)
        ];
        foreach (var (error, code) in failures)
        {
            var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
            using var source = new FailingSource(error);
            var failed = Assert.IsType<ArtifactResult<ArtifactStagedWrite>.Failure>(
                await driver.Store.StageAsync(ticket, source, new(), default));
            Assert.Equal(code, failed.Code);
            ArtifactTestData.AssertSanitized(failed.ToString());
            Assert.False(source.WasDisposed);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        }
        using var valid = new ShortSource("valid after failed private staging"u8.ToArray());
        var committed = await PublishAsync(driver, valid, new(1024));
        Assert.Equal("valid after failed private staging"u8.ToArray(), await ReadAsync(driver, committed.Stamp));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource("decision survives unexpected failure"u8.ToArray());
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        ValueTask Fault() => ValueTask.FromException(new InvalidOperationException(ArtifactTestData.Canary));
        if (driver.LocalControls is { } local) { local.SetObserver("publish.decided", Fault); }
        else { driver.ObjectControls!.SetObserver("pointer.selected", Fault); }
        var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
            await driver.Store.CommitAsync(staged, new(), default));
        Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
        Assert.Equal(ArtifactAction.ReconcileExactTicket, failed.Action);
        ArtifactTestData.AssertSanitized(failed.ToString());
        var resolution = Assert.IsType<ArtifactResolution.Committed>(
            Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
        Assert.Equal("decision survives unexpected failure"u8.ToArray(), await ReadAsync(driver, resolution.Receipt.Stamp));
        Assert.Equal(resolution.Receipt, Success(await driver.Store.CommitAsync(staged, new(), default)));
    }

    private sealed class FailingSource(Exception error) : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
            => ValueTask.FromException<int>(error);
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
