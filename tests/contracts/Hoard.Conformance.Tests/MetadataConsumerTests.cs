using Hoard.Abstractions.Metadata;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Conformance.Tests;

public sealed class MetadataConsumerTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Writer_contention_failure_releases_exclusion_and_joins_uncancelled_settlement(bool cancelCaller)
    {
        using var cancellation = new CancellationTokenSource();
        await using var store = new SuccessfulLosers(() => { if (cancelCaller) { cancellation.Cancel(); } });
        var hold = new ObservedWriterHold();
        var settlementEntered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var settlementReleased = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var checking = MetadataReconciliationAssertions.WriterContentionAsync(store,
            _ => ValueTask.FromResult<IAsyncDisposable>(hold), token =>
            {
                Assert.True(hold.Released);
                Assert.False(token.CanBeCanceled);
                settlementEntered.TrySetResult();
                return new(settlementReleased.Task);
            }, cancellation.Token);
        try
        {
            await Assert.ThrowsAsync<TimeoutException>(() => checking.WaitAsync(TimeSpan.FromMilliseconds(200)));
            await settlementEntered.Task.WaitAsync(TimeSpan.FromSeconds(5));
        }
        finally
        {
            settlementReleased.TrySetResult();
            var failure = Assert.IsType<Xunit.Sdk.XunitException>(await Record.ExceptionAsync(() => checking));
            Assert.Equal("Unexpected reconcile.", failure.Message);
        }
    }

    [Fact]
    public async Task Competing_create_consumer_rejects_successful_losers_instead_of_accepting_provider_results()
    {
        await using var store = new SuccessfulLosers();
        await Assert.ThrowsAsync<Xunit.Sdk.SingleException>(
            () => MetadataConcurrencyAssertions.CompetingCreatesAsync(store, default));
        Assert.Equal(8, store.Commits);
    }

    [Fact]
    public async Task Common_consumer_propagates_cancellation_to_the_store_without_publishing_a_candidate()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await using var store = new SuccessfulLosers();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => MetadataConcurrencyAssertions.CompetingCreatesAsync(store, cancellation.Token));
        Assert.Equal(0, store.Commits);
    }

    private sealed class ObservedWriterHold : IAsyncDisposable
    {
        public bool Released { get; private set; }
        public ValueTask DisposeAsync()
        {
            Released = true;
            return ValueTask.CompletedTask;
        }
    }

    private sealed class SuccessfulLosers(Action? onReconcile = null) : IMetadataStore
    {
        public int Commits { get; private set; }
        public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
            MetadataCallOptions options, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return ValueTask.FromResult<MetadataResult<MetadataOperationTicket>>(
                new MetadataResult<MetadataOperationTicket>.Success(
                    new(new(Guid.NewGuid()), new(Guid.NewGuid()), new(0), new(86400000))));
        }

        public ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
            MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            Commits++;
            var registry = Assert.IsType<MetadataMutation.PutRegistry>(Assert.Single(request.Mutations)).Record;
            return ValueTask.FromResult<MetadataResult<MetadataCommitReceipt>>(
                new MetadataResult<MetadataCommitReceipt>.Success(new(request.Ticket, new(Guid.NewGuid()),
                    [new(registry.Selector, new MetadataOption<MetadataRevision>.Some(registry.Revision))], [])));
        }

        public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
            MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken) =>
            throw new Xunit.Sdk.XunitException("Unexpected read after contradictory commits.");

        public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
            MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken) =>
            throw new Xunit.Sdk.XunitException("Unexpected page after contradictory commits.");

        public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
            MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken)
        {
            onReconcile?.Invoke();
            throw new Xunit.Sdk.XunitException("Unexpected reconcile.");
        }

        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
