using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Artifacts;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactReadVerificationTests
{
    [Fact]
    public async Task Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        await using var reading = new ArtifactTestBarrier("corrupt-read-before-final-digest");
        await using var verifying = new ArtifactTestBarrier("reconciliation-before-final-state");
        await ArtifactReadAssertions.ReconciliationQuarantineRaceAsync(driver.Store,
            () => driver.LocalControls!.SetObserver("publish.decided",
                () => ValueTask.FromException(new IOException(ArtifactTestData.Canary))),
            () => driver.LocalControls!.RemoveObserver("publish.decided"),
            () => driver.DamageOnlyPayload(truncate: false),
            () => driver.LocalControls!.SetObserver("read.copy", () => new(reading.HoldAsync())),
            () => driver.LocalControls!.SetObserver("reconcile.verified", () => new(verifying.HoldAsync())),
            token => reading.Entered.WaitAsync(token), token => verifying.Entered.WaitAsync(token),
            reading.Release, verifying.Release,
            bytes => File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes), default);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Admitted_open_rechecks_quarantine_before_delivering_a_session(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await using var barrier = new ArtifactTestBarrier("open-quarantine-revalidation");
        string? path = null;
        await ArtifactReadAssertions.AdmittedOpenRechecksQuarantineAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity,
            () => SetObserver(driver, "read.opened", "object.direct", () => new(barrier.HoldAsync())),
            token => barrier.Entered.WaitAsync(token),
            () =>
            {
                if (driver.LocalControls is { } local) { local.RemoveObserver("read.opened"); }
                else { driver.ObjectControls!.RemoveObserver("object.direct"); }
            },
            bytes =>
            {
                path ??= Directory.GetFiles(driver.PayloadDirectory).Single();
                File.WriteAllBytes(path, bytes);
            }, barrier.Release, default);
    }

    [Theory]
    [InlineData("local", "open")]
    [InlineData("local", "publication")]
    [InlineData("local", "reconciliation")]
    [InlineData("object", "open")]
    [InlineData("object", "publication")]
    [InlineData("object", "reconciliation")]
    public async Task Every_committed_detection_path_quarantines_restored_bytes(string provider, string detection)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var expectedDurability = provider switch
        {
            "local" => ArtifactDurability.LocalProcessCrash,
            "object" => ArtifactDurability.SimulationOnly,
            _ => throw new ArgumentException("Unknown frozen test variant.")
        };
        string? removedPath = null;
        await ArtifactReadAssertions.CommittedDetectionQuarantineAsync(driver.Store, detection, expectedDurability,
            () =>
            {
                removedPath = Directory.GetFiles(driver.PayloadDirectory).Single();
                File.Delete(removedPath);
            },
            bytes => File.WriteAllBytes(
                removedPath ?? throw new InvalidOperationException("Payload was not removed."), bytes),
            () => SetObserver(driver, "publish.decided", "pointer.selected", () =>
            {
                if (detection == "reconciliation") { return ValueTask.FromException(new IOException(ArtifactTestData.Canary)); }
                driver.DamageOnlyPayload(truncate: true);
                return ValueTask.CompletedTask;
            }),
            () =>
            {
                if (driver.LocalControls is { } local) { local.RemoveObserver("publish.decided"); }
                else { driver.ObjectControls!.RemoveObserver("pointer.selected"); }
            },
            () => driver.DamageOnlyPayload(truncate: false),
            bytes => File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes),
            default, ArtifactEvidenceTests.QuarantineReopen(driver));
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence(string provider, bool truncate)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        string? path = null;
        await ArtifactReadAssertions.DamagedReadAsync(
            driver.Store, driver.Validator, driver.Authority, driver.Identity, truncate,
            () =>
            {
                path = Directory.GetFiles(driver.PayloadDirectory).Single();
                return ValueTask.FromResult(File.ReadAllBytes(path));
            },
            damage => { driver.DamageOnlyPayload(damage); return ValueTask.CompletedTask; },
            bytes =>
            {
                File.WriteAllBytes(path ?? throw new InvalidOperationException("Payload was not captured."), bytes);
                return ValueTask.CompletedTask;
            }, default, ArtifactEvidenceTests.QuarantineReopen(driver));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        await ArtifactReadAssertions.DestinationFailureAsync(driver.Store, ArtifactTestData.Canary, default);
    }
}
