using Hoard.Abstractions.Storage;
using static Hoard.Artifacts.Tests.ArtifactPublicationTests;

namespace Hoard.Artifacts.Tests;

public sealed class ArtifactFailureTests
{
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
