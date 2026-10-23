using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactReadVerificationTests
{
    [Fact]
    public async Task Local_reconciliation_cannot_finalize_after_overlapping_read_quarantines_the_incarnation()
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync("local");
        var bytes = "read detection wins before reconciliation settles"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        driver.LocalControls!.SetObserver("publish.decided", () => ValueTask.FromException(new IOException(ArtifactTestData.Canary)));
        Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(staged, new(), default));
        driver.LocalControls.RemoveObserver("publish.decided");
        driver.DamageOnlyPayload(truncate: false);
        await using var session = Success(await driver.Store.OpenReadAsync(new(staged.Identity.Digest), new(), default));
        await using var reading = new ArtifactTestBarrier("corrupt-read-before-final-digest");
        await using var verifying = new ArtifactTestBarrier("reconciliation-before-final-state");
        driver.LocalControls.SetObserver("read.copy", () => new(reading.HoldAsync()));
        driver.LocalControls.SetObserver("reconcile.verified", () => new(verifying.HoldAsync()));
        using var destination = new MemoryStream();
        var copying = session.CopyToAsync(destination, new(), default).AsTask();
        Task<ArtifactResult<ArtifactResolution>>? reconciling = null;
        try
        {
            await reading.Entered;
            File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes);
            reconciling = driver.Store.ReconcileAsync(ticket, new(), default).AsTask();
            await verifying.Entered;
            reading.Release();
            Assert.Equal(ArtifactFailureCode.CorruptContent,
                Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await copying).Code);
        }
        finally { reading.Release(); verifying.Release(); }
        Assert.NotNull(reconciling);
        Assert.Equal(ArtifactFailureCode.CorruptContent,
            Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await reconciling).Code);
        Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(await driver.Store.ReconcileAsync(ticket, new(), default));
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Admitted_open_rechecks_quarantine_before_delivering_a_session(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        var bytes = "late open cannot bypass quarantine"u8.ToArray();
        using var source = new ShortSource(bytes);
        var receipt = await PublishAsync(driver, source, new(1024));
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using var barrier = new ArtifactTestBarrier("open-quarantine-revalidation");
        SetObserver(driver, "read.opened", "object.direct", () => new(barrier.HoldAsync()));
        var opening = driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default).AsTask();
        try
        {
            await barrier.Entered;
            if (driver.LocalControls is { } local) { local.RemoveObserver("read.opened"); }
            else { driver.ObjectControls!.RemoveObserver("object.direct"); }
            var path = Directory.GetFiles(driver.PayloadDirectory).Single();
            File.WriteAllBytes(path, bytes[..^1]);
            await using var guard = Success(await driver.Authority.AcquireAsync(new(Guid.NewGuid(),
                ArtifactProtectionOperation.Reference, driver.Identity, receipt.Stamp.Identity.Digest,
                new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp)), new(), default));
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(
                await driver.Validator.ValidateAsync(proof, guard, new(), default)).Code);
            File.WriteAllBytes(path, bytes);
        }
        finally { barrier.Release(); }
        var result = await opening;
        if (result is ArtifactResult<IArtifactReadSession>.Success leaked) { await leaked.Value.DisposeAsync(); }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(result).Code);
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
        var bytes = "quarantine at each committed detection boundary"u8.ToArray();
        using var source = new ShortSource(bytes);
        var ticket = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
        var staged = Success(await driver.Store.StageAsync(ticket, source, new(), default));
        ArtifactMutationReceipt receipt;
        if (detection == "open")
        {
            receipt = Success(await driver.Store.CommitAsync(staged, new(), default));
            var path = Directory.GetFiles(driver.PayloadDirectory).Single();
            File.Delete(path);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await driver.Store.OpenReadAsync(new(staged.Identity.Digest), new(), default)).Code);
            File.WriteAllBytes(path, bytes);
        }
        else
        {
            SetObserver(driver, "publish.decided", "pointer.selected", () =>
            {
                if (detection == "reconciliation") { return ValueTask.FromException(new IOException(ArtifactTestData.Canary)); }
                driver.DamageOnlyPayload(truncate: true);
                return ValueTask.CompletedTask;
            });
            Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(await driver.Store.CommitAsync(staged, new(), default));
            if (driver.LocalControls is { } local) { local.RemoveObserver("publish.decided"); }
            else { driver.ObjectControls!.RemoveObserver("pointer.selected"); }
            if (detection == "reconciliation")
            {
                driver.DamageOnlyPayload(truncate: false);
                Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await driver.Store.ReconcileAsync(ticket, new(), default));
            }
            File.WriteAllBytes(Directory.GetFiles(driver.PayloadDirectory).Single(), bytes);
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
                await driver.Store.OpenReadAsync(new(staged.Identity.Digest), new(), default)).Code);
            if (detection == "reconciliation" || provider == "object")
            {
                Assert.IsType<ArtifactResult<ArtifactResolution>.Failure>(
                    await driver.Store.ReconcileAsync(ticket, new(), default));
                using var duplicate = new ShortSource(bytes);
                var retry = Success(await driver.Store.ReserveWriteAsync(new(new ArtifactExpectations(1024)), new(), default));
                var restaged = Success(await driver.Store.StageAsync(retry, duplicate, new(), default));
                Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactMutationReceipt>.Failure>(
                    await driver.Store.CommitAsync(restaged, new(), default)).Code);
                Success(await driver.Store.AbandonAsync(restaged.Owner, new(), default));
                return;
            }
            receipt = Assert.IsType<ArtifactResolution.Committed>(
                Success(await driver.Store.ReconcileAsync(ticket, new(), default))).Receipt;
        }
        await ArtifactEvidenceTests.AssertQuarantinedAsync(driver, receipt, bytes);
    }

    [Theory]
    [InlineData("local", false)]
    [InlineData("local", true)]
    [InlineData("object", false)]
    [InlineData("object", true)]
    public async Task Damaged_read_has_no_completion_and_invalidates_later_health_and_evidence(string provider, bool truncate)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("detect stored corruption"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        var path = Directory.GetFiles(driver.PayloadDirectory).Single();
        var bytes = File.ReadAllBytes(path);
        driver.DamageOnlyPayload(truncate);
        var proof = Assert.IsType<ArtifactOption<ArtifactCommitEvidence>.Some>(receipt.Evidence).Value;
        await using (var session = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)))
        {
            using var destination = new MemoryStream();
            Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(
                await session.CopyToAsync(destination, new(), default)).Code);
            Assert.True(destination.CanWrite);
        }
        Assert.Equal(ArtifactFailureCode.CorruptContent, Assert.IsType<ArtifactResult<IArtifactReadSession>.Failure>(
            await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default)).Code);
        var scope = new ArtifactProtectionRequest(Guid.NewGuid(), ArtifactProtectionOperation.Reference,
            driver.Identity, receipt.Stamp.Identity.Digest, new ArtifactOption<ArtifactStamp>.Some(receipt.Stamp));
        await using var guard = Success(await driver.Authority.AcquireAsync(scope, new(), default));
        Assert.IsType<ArtifactResult<ArtifactStamp>.Failure>(await driver.Validator.ValidateAsync(proof, guard, new(), default));
        File.WriteAllBytes(path, bytes);
        await guard.DisposeAsync();
        await ArtifactEvidenceTests.AssertQuarantinedAsync(driver, receipt, bytes);
    }

    [Theory]
    [InlineData("local")]
    [InlineData("object")]
    public async Task Destination_failure_and_second_copy_never_return_verified_completion_or_dispose_borrowed_streams(string provider)
    {
        await using var driver = await ArtifactProviderDriver.CreateAsync(provider);
        using var source = new ShortSource("borrowed streams"u8.ToArray());
        var receipt = await PublishAsync(driver, source, new(1024));
        await using var session = Success(await driver.Store.OpenReadAsync(new(receipt.Stamp.Identity.Digest), new(), default));
        using var destination = new FailingDestination();
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await session.CopyToAsync(destination, new(), default));
        Assert.False(destination.WasDisposed);
        Assert.False(source.WasDisposed);
        Assert.IsType<ArtifactResult<ArtifactReadCompletion>.Failure>(await session.CopyToAsync(Stream.Null, new(), default));
    }

    private sealed class FailingDestination : MemoryStream
    {
        public bool WasDisposed { get; private set; }
        public override ValueTask WriteAsync(ReadOnlyMemory<byte> buffer, CancellationToken cancellationToken = default)
            => ValueTask.FromException(new IOException(ArtifactTestData.Canary));
        protected override void Dispose(bool disposing) { WasDisposed = true; base.Dispose(disposing); }
    }
}
