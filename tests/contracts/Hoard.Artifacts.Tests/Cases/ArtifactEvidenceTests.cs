using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactEvidenceTests
{
    [Fact]
    public async Task Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        var bytes = "quarantine survives denied decision persistence"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, source, new(1024));
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        var path = Directory.GetFiles(driver.PayloadDirectory).Single();
        var decisions = Path.Combine(Path.GetDirectoryName(driver.PayloadDirectory)!, "decisions");
        driver.DamageOnlyPayload(truncate: true);
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
        try
        {
            File.SetUnixFileMode(decisions, UnixFileMode.UserRead | UnixFileMode.UserExecute);
            await using var guard = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Reference, driver.Identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
            var failed = Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, guard, new(), default));
            Assert.Equal(ArtifactFailureCode.AccessDenied, failed.Code);
            File.WriteAllBytes(path, bytes);
            Assert.False(driver.Ready);
            Assert.Equal(ArtifactCleanupState.RetainedLiveOwnership, failed.Cleanup);
            Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default));
            Assert.IsType<ArtifactResult<ArtifactShutdown>.Failure>(await driver.StopAsync(new(TimeSpan.FromSeconds(1))));
        }
        finally { File.SetUnixFileMode(decisions, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
        Success(await driver.StopAsync(new()));
        Success(await ((IArtifactStoreLifetime)driver.Store).InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
            driver.Identity, driver.Authority), new(), default));
        await AssertQuarantinedAsync(driver, receipt, bytes);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Validation_first_corruption_cannot_be_revived_by_external_restoration(string provider, bool missing)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider,
            references: (_, _) => ValueTask.FromResult(new ArtifactReferenceDecision(true, 0, Guid.NewGuid())));
        var bytes = "validation must quarantine this incarnation"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, source, new(1024));
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        var request = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            driver.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using (var protection = Success(await driver.Authority.AcquireAsync(request, new(), default)))
        {
            Assert.Equal(receipt.Stamp, Success(await driver.Validator.ValidateAsync(proof, protection, new(), default)));
            var path = Directory.GetFiles(driver.PayloadDirectory).Single();
            if (missing) { File.Delete(path); }
            else { driver.DamageOnlyPayload(truncate: true); }
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, protection, new(), default)).Code);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
            File.WriteAllBytes(path, bytes);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, protection, new(), default)).Code);
        }
        await AssertQuarantinedAsync(driver, receipt, bytes);
        var deletion = Success(await driver.Store.ReserveDeleteAsync(new(receipt.Stamp), new(), default));
        Success(await driver.Store.DeleteAsync(deletion, new(), default));
        using var replacementSource = new ShortSource(bytes);
        var replacement = await PublishAsync(driver, replacementSource, new(1024));
        Assert.NotEqual(receipt.Stamp.Incarnation, replacement.Stamp.Incarnation);
        Assert.Equal(receipt, Assert.IsType<ArtifactResolution.Committed>(
            Success(await driver.Store.ReconcileAsync(receipt.Ticket, new(), default))).Receipt);
        Assert.Equal(bytes, await ReadAsync(driver, replacement.Stamp));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Validation_access_failure_does_not_quarantine_intact_content(string provider, bool unavailable)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "permission failure is not corruption"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, source, new(1024));
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using var guard = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
            ArtifactProtectionOperation.Reference, driver.Identity, receipt.Stamp.Identity.Digest,
            new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
        var path = Directory.GetFiles(driver.PayloadDirectory).Single();
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
        try
        {
            if (unavailable) { Directory.Move(driver.PayloadDirectory, driver.PayloadDirectory + "-offline"); }
            else { File.SetUnixFileMode(path, UnixFileMode.UserWrite); }
            Assert.Equal(unavailable ? ArtifactFailureCode.Unavailable : ArtifactFailureCode.AccessDenied,
                Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, guard, new(), default)).Code);
        }
        finally
        {
            if (unavailable) { Directory.Move(driver.PayloadDirectory + "-offline", driver.PayloadDirectory); }
            else { File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite); }
        }
        Assert.Equal(receipt.Stamp, Success(await driver.Validator.ValidateAsync(proof, guard, new(), default)));
        Assert.Equal(bytes, await ReadAsync(driver, receipt.Stamp));
    }

    internal static async Task AssertQuarantinedAsync(ArtifactProviderDriver driver, ArtifactMutationReceipt receipt, byte[] bytes)
    {
        await ArtifactEvidenceAssertions.QuarantineIsPermanentAsync(driver.Store, receipt, bytes, default);
        if (driver.ProviderId == "local")
        {
            Success(await driver.StopAsync(new()));
            var reopened = new LocalArtifactStore(Path.GetDirectoryName(driver.PayloadDirectory)!);
            try
            {
                Success(await reopened.InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                    driver.Identity, driver.Authority), new(), default));
                Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                    await reopened.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
            }
            finally { Success(await reopened.StopAsync(new(), default)); }
            Success(await ((IArtifactStoreLifetime)driver.Store).InitializeAsync(new(ArtifactInitializationMode.ReopenCompatible,
                driver.Identity, driver.Authority), new(), default));
        }
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Only_exact_current_receipts_with_opaque_same_operation_protection_validate(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactEvidenceAssertions.ExactCurrentReceiptsAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity, default);
    }
}
