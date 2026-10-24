using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactFailureTests
{
    [Fact]
    public async Task Reused_object_receipt_survives_failed_unselected_assembly_cleanup()
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
        await using var driver = await ArtifactProviderDriver.CreateAsync("object",
            limits: new(artifactBytes: 1024, stagingBytes: 1024));
        var bytes = "reused selected object stays immutable"u8.ToArray();
        using var control = new ShortSource(bytes);
        var committed = await PublishAsync(driver, control, new(1024));
        var objects = Path.Combine(Path.GetDirectoryName(driver.StagingDirectory)!, "objects");
        var selected = Assert.Single(Directory.GetFiles(objects));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        using var source = new ShortSource(bytes);
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        driver.ObjectControls!.SetObserver("object.direct", () =>
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserExecute);
            return ValueTask.CompletedTask;
        });
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), default));
            Assert.Equal(ArtifactFailureCode.Uncertain, failed.Code);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(driver.Ready);
            driver.ObjectControls.RemoveObserver("object.direct");
            var receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
            Assert.Equal(ArtifactMutationOutcome.AlreadyPresentVerified, receipt.Outcome);
            Assert.Equal(committed.Stamp, receipt.Stamp);
            Assert.Equal(2, Directory.GetFiles(objects).Length);
            var row = Assert.Single(Success(await driver.Maintenance.ObserveAsync(
                new(driver.Identity, ArtifactRecoveryKind.Staging), new(), default)).Observations);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            var request = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            Assert.Equal(ArtifactFailureCode.AccessDenied, Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                await driver.Maintenance.CleanupAsync(request, new(), default)).Code);
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            var reclaimed = Success(await driver.Maintenance.CleanupAsync(request, new(), default));
            Assert.Equal(2 * bytes.Length, reclaimed.ReclaimedBytes);
            Assert.Equal(selected, Assert.Single(Directory.GetFiles(objects)));
            Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
            Assert.True(driver.Ready);
            Assert.Equal(receipt, Success(await driver.Store.CommitAsync(staged, new(), default)));
            Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt);
            Assert.Equal(bytes, await ReadAsync(driver, committed.Stamp));
            Assert.False(source.WasDisposed);
            Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        }
        finally
        {
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            driver.ObjectControls.RemoveObserver("object.direct");
        }
    }

    [Theory]
    [InlineData("object.commit-progress", false)]
    [InlineData("pointer.compare", false)]
    [InlineData("object.commit-progress", true)]
    [InlineData("pointer.compare", true)]
    public async Task Unselected_object_cleanup_retains_exact_ownership_and_blocks_retry_until_reclaimed(string boundary, bool cancel)
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
        const int length = 512 * 1024;
        await using var driver = await ArtifactProviderDriver.CreateAsync("object",
            limits: new(artifactBytes: length, stagingBytes: length));
        using var control = new ShortSource("selected payload must survive scratch cleanup"u8.ToArray());
        var committed = await PublishAsync(driver, control, new(length));
        var objects = Path.Combine(Path.GetDirectoryName(driver.StagingDirectory)!, "objects");
        var selected = Assert.Single(Directory.GetFiles(objects));
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(length)), new(), default));
        using var source = new ShortSource(new byte[length]);
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        using var cancellation = new CancellationTokenSource();
        driver.ObjectControls!.SetObserver(boundary, () =>
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserExecute);
            if (cancel) { cancellation.Cancel(); return ValueTask.CompletedTask; }
            return ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        });
        try
        {
            var failed = Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                await driver.Store.CommitAsync(staged, new(), cancellation.Token));
            await driver.WhenIdleAsync();
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.False(driver.Ready);
            Assert.False(source.WasDisposed);
            var residual = Assert.Single(Directory.GetFiles(objects), path => path != selected);
            var residualBytes = new FileInfo(residual).Length;
            Assert.InRange(residualBytes, 1, length);
            if (boundary == "object.commit-progress") { Assert.True(residualBytes < length); }
            else { Assert.Equal(length, residualBytes); }
            for (var attempt = 0; attempt < 3; attempt++)
            {
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await driver.Store.CommitAsync(staged, new(), default)).Code);
                Assert.Equal(ArtifactFailureCode.CleanupIncomplete, Assert.IsType<ArtifactResult<ArtifactOperationTicket>.Failure>(
                    await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(length)), new(), default)).Code);
                Assert.Equal(2, Directory.GetFiles(objects).Length);
            }
            var page = Success(await driver.Maintenance.ObserveAsync(
                new(driver.Identity, ArtifactRecoveryKind.Staging), new(), default));
            var row = Assert.Single(page.Observations);
            Assert.Equal(ArtifactObservationKind.AbandonedStaging, row.Kind);
            var owner = Assert.IsType<ArtifactOption<ArtifactStagingOwner>.Some>(row.Owner).Value;
            Assert.Equal(staged.Owner, owner);
            var request = new ArtifactCleanupRequest(driver.Identity, [new ArtifactCleanupTarget.AbandonedStaging(owner)]);
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var retry = Assert.IsType<ArtifactResult<ArtifactCleanupReport>.Failure>(
                    await driver.Maintenance.CleanupAsync(request, new(), default));
                Assert.Equal(ArtifactFailureCode.AccessDenied, retry.Code);
                Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, retry.Cleanup);
            }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            driver.ObjectControls.RemoveObserver(boundary);
            var reclaimed = Success(await driver.Maintenance.CleanupAsync(request, new(), default));
            Assert.Equal(1, reclaimed.Completed);
            Assert.Equal(length + residualBytes, reclaimed.ReclaimedBytes);
            Assert.Equal(selected, Assert.Single(Directory.GetFiles(objects)));
            Assert.Empty(Directory.GetFiles(driver.StagingDirectory));
            Assert.True(driver.Ready);
            Assert.IsType<ArtifactResolution.NotCommitted>(Success(await driver.Store.ReconcileAsync(ticket, new(), default)));
            Assert.Equal("selected payload must survive scratch cleanup"u8.ToArray(), await ReadAsync(driver, committed.Stamp));
            using var replacement = new ShortSource("fresh selected object after cleanup"u8.ToArray());
            var fresh = await PublishAsync(driver, replacement, new(length));
            Assert.Equal(1, Success(await driver.Maintenance.CleanupAsync(request, new(), default)).Conflicted);
            Assert.Equal("fresh selected object after cleanup"u8.ToArray(), await ReadAsync(driver, fresh.Stamp));
        }
        finally
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
            File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            driver.ObjectControls.RemoveObserver(boundary);
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Committed_receipts_remain_reconcilable_while_exact_residual_staging_is_reclaimed(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            limits: new(artifactBytes: 1024, stagingBytes: 1024));
        await CleanupAssertions(driver).CommittedResidualAsync(() =>
        {
            if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix staging proof required."); }
            File.SetUnixFileMode(driver.StagingDirectory, UnixFileMode.UserRead | UnixFileMode.UserExecute);
        }, () => RestorePrefixCleanup(driver), default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Failed_prefix_reclamation_retains_ownership_until_exact_bounded_cleanup(string provider)
    {
        var clock = new ArtifactTestClock();
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider, clock,
            new(artifactBytes: 1024, stagingBytes: 1024));
        await CleanupAssertions(driver).FailedPrefixAsync(
            () => DenyPrefixCleanup(driver), () => RestorePrefixCleanup(driver), default);
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
        await CleanupAssertions(driver).FailedPrefixStopAsync(
            ticket, source, driver.StopAsync, () => RestorePrefixCleanup(driver), default);
        if (provider == "local")
        {
            var reopened = new LocalArtifactStore(Path.GetDirectoryName(driver.StagingDirectory)!);
            Success(await reopened.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible, driver.Identity,
                driver.Authority, new(artifactBytes: 1024, stagingBytes: 1024)), new(), default));
            try
            {
                await ArtifactCleanupAssertions.ReopenedAfterPrefixStopAsync(reopened, () => reopened.Ready, ticket, default);
            }
            finally { Success(await reopened.StopAsync(new(), default)); }
        }
    }

    private static ArtifactCleanupAssertions CleanupAssertions(ArtifactProviderDriver driver) =>
        new(driver.Store, driver.Maintenance, driver.Identity, () => driver.Ready,
            () => Directory.GetFiles(driver.StagingDirectory));

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
        await ArtifactFailureAssertions.StorageFailuresAsync(driver.Store, default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Unexpected_fault_after_visibility_requires_exact_ticket_reconciliation(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactFailureAssertions.UnexpectedFaultAsync(driver.Store, () =>
        {
            ValueTask Fault() => ValueTask.FromException(new InvalidOperationException(ArtifactTestData.Canary));
            if (driver.LocalControls is { } local) { local.SetObserver("publish.decided", Fault); }
            else { driver.ObjectControls!.SetObserver("pointer.selected", Fault); }
        }, default);
    }
}
