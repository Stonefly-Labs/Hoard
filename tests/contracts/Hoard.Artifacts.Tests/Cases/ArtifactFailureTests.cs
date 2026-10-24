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
        var objects = Path.Combine(Path.GetDirectoryName(driver.StagingDirectory)!, "objects");
        await CleanupAssertions(driver).ReusedObjectAsync(() => Directory.GetFiles(objects),
            () => driver.ObjectControls!.SetObserver("object.direct", () =>
            {
                if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
                File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserExecute);
                return ValueTask.CompletedTask;
            }), () => driver.ObjectControls!.RemoveObserver("object.direct"),
            () => RestoreObjectCleanup(objects), default);
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
        var objects = Path.Combine(Path.GetDirectoryName(driver.StagingDirectory)!, "objects");
        await CleanupAssertions(driver).UnselectedObjectAsync(boundary == "object.commit-progress",
            () => Directory.GetFiles(objects), residual => new FileInfo(residual).Length, driver.WhenIdleAsync,
            cancellation => driver.ObjectControls!.SetObserver(boundary, () =>
            {
                if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
                File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserExecute);
                if (cancel) { cancellation.Cancel(); return ValueTask.CompletedTask; }
                return ValueTask.FromException(new IOException(ArtifactTestData.Canary));
            }), () => driver.ObjectControls!.RemoveObserver(boundary),
            () => RestoreObjectCleanup(objects),
            () =>
            {
                RestoreObjectCleanup(objects);
                driver.ObjectControls!.RemoveObserver(boundary);
            }, default);
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

    private static void RestoreObjectCleanup(string objects)
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix object proof required."); }
        File.SetUnixFileMode(objects, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
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
