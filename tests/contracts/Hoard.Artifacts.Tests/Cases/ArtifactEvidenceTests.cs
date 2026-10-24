using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Testing.Conformance.Artifacts;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactEvidenceTests
{
    [Fact]
    public async Task Local_failed_quarantine_persistence_retains_ownership_until_stop_retry_and_reopen()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        string? path = null;
        string? decisions = null;
        await ArtifactEvidenceAssertions.FailedQuarantinePersistenceAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity,
            (IArtifactStoreLifetime)driver.Store, () => driver.Ready,
            () =>
            {
                path = Directory.GetFiles(driver.PayloadDirectory).Single();
                decisions = Path.Combine(Path.GetDirectoryName(driver.PayloadDirectory)!, "decisions");
            },
            () => driver.DamageOnlyPayload(truncate: true), RequireUnixPermissionProof,
            () => SetUnixPermissions(decisions ?? throw new InvalidOperationException("Decision path was not captured."),
                UnixFileMode.UserRead | UnixFileMode.UserExecute),
            bytes => File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not captured."), bytes),
            () => SetUnixPermissions(decisions ?? throw new InvalidOperationException("Decision path was not captured."),
                UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute),
            default, QuarantineReopen(driver));
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
        string? path = null;
        await ArtifactEvidenceAssertions.ValidationFirstCorruptionAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity,
            () =>
            {
                path = Directory.GetFiles(driver.PayloadDirectory).Single();
                if (missing) { File.Delete(path); }
                else { driver.DamageOnlyPayload(truncate: true); }
            },
            bytes => File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not captured."), bytes),
            default, QuarantineReopen(driver));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Validation_access_failure_does_not_quarantine_intact_content(string provider, bool unavailable)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        string? path = null;
        await ArtifactEvidenceAssertions.ValidationAccessFailureAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity, unavailable,
            () =>
            {
                path = Directory.GetFiles(driver.PayloadDirectory).Single();
                RequireUnixPermissionProof();
            },
            () =>
            {
                if (unavailable) { Directory.Move(driver.PayloadDirectory, driver.PayloadDirectory + "-offline"); }
                else { SetUnixPermissions(path ?? throw new InvalidOperationException("Payload was not captured."), UnixFileMode.UserWrite); }
            },
            () =>
            {
                if (unavailable) { Directory.Move(driver.PayloadDirectory + "-offline", driver.PayloadDirectory); }
                else { SetUnixPermissions(path ?? throw new InvalidOperationException("Payload was not captured."),
                    UnixFileMode.UserRead | UnixFileMode.UserWrite); }
            }, default);
    }

    private static void RequireUnixPermissionProof()
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
    }

    private static void SetUnixPermissions(string path, UnixFileMode mode)
    {
        if (OperatingSystem.IsWindows()) { throw new PlatformNotSupportedException("Private Unix permission proof required."); }
        File.SetUnixFileMode(path, mode);
    }

    internal static ArtifactQuarantineReopen? QuarantineReopen(ArtifactProviderDriver driver) =>
        driver.ProviderId switch
        {
            "local" => new((IArtifactStoreLifetime)driver.Store, driver.Identity, driver.Authority, () =>
            {
                var reopened = new LocalArtifactStore(Path.GetDirectoryName(driver.PayloadDirectory)!);
                return (reopened, reopened);
            }),
            "object" => null,
            _ => throw new ArgumentException("Unknown frozen test variant.")
        };

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
