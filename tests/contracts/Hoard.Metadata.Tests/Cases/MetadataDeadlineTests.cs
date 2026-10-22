using Hoard.Abstractions.Metadata;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataDeadlineTests
{
    [Fact]
    public async Task MP19_Actual_writer_contention_consumes_the_original_budget_without_committing()
    {
        await using var fixture = await OpenAsync();
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        using (await fixture.HoldWriterForTestAsync())
        {
            var elapsed = System.Diagnostics.Stopwatch.StartNew();
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await fixture.Store.CommitAsync(batch,
                new(TimeSpan.FromMilliseconds(50)), default)));
            Assert.True(elapsed.Elapsed < TimeSpan.FromSeconds(2));
            await fixture.WhenIdleAsync();
            await Missing(fixture, Registry().Selector);
        }
        Success(await fixture.Store.CommitAsync(batch, new(), default));
        await Read<MetadataRegistry>(fixture, Registry().Selector);
    }

    [Fact]
    public async Task MP37_Incomplete_cleanup_reports_failure_and_keeps_activity_owned()
    {
        var fixture = await OpenAsync();
        await using var barrier = new MetadataTestBarrier(TimeSpan.FromSeconds(60));
        fixture.Controls.SetObserver("M0", () => new(barrier.HoldAsync()));
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var committing = fixture.Store.CommitAsync(batch, new(TimeSpan.FromMilliseconds(200)), default).AsTask();
        await barrier.Entered;
        try
        {
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await committing));
            var error = await Assert.ThrowsAsync<InvalidOperationException>(() => fixture.DisposeAsync().AsTask());
            Assert.Contains("cleanup incomplete", error.Message);
            Assert.Contains("metadata.cleanup_incomplete", fixture.Controls.Diagnostics);
            Assert.False(fixture.WhenIdleAsync().IsCompleted);
            Assert.Equal(MetadataFailureCode.Disposed, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        }
        finally { barrier.Release(); await fixture.WhenIdleAsync(); await fixture.DisposeAsync(); }
    }

    [Fact]
    public async Task MP18_Cancellation_before_decision_is_definite_and_after_attempt_is_uncertain()
    {
        await using var fixture = await OpenAsync();
        using var alreadyCancelled = new CancellationTokenSource();
        alreadyCancelled.Cancel();
        Assert.Equal(MetadataFailureCode.CancelledBeforeCommit, Failed(await fixture.Store.ReserveOperationAsync(new(), alreadyCancelled.Token)));
        foreach (var point in new[] { "M0", "M1" })
        {
            await using var barrier = new MetadataTestBarrier();
            using var cancellation = new CancellationTokenSource();
            var registry = Registry(point == "M0" ? 1 : 2);
            var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
            fixture.Controls.SetObserver(point, () => new(barrier.HoldAsync()));
            var committing = fixture.Store.CommitAsync(batch, new(), cancellation.Token).AsTask();
            await barrier.Entered;
            cancellation.Cancel();
            Assert.Equal(point == "M0" ? MetadataFailureCode.CancelledBeforeCommit : MetadataFailureCode.Uncertain, Failed(await committing));
            Assert.Equal(MetadataFailureCode.Unavailable, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
            barrier.Release();
            await fixture.WhenIdleAsync();
            fixture.Controls.RemoveObserver(point);
            var resolution = Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default));
            if (point == "M0")
            {
                Assert.IsType<MetadataResolution.NotCommitted>(resolution);
                await Missing(fixture, registry.Selector);
            }
            else
            {
                Assert.IsType<MetadataResolution.Committed>(resolution);
                await Read<MetadataRegistry>(fixture, registry.Selector);
            }
        }
    }

    [Fact]
    public async Task MP19_Queue_capacity_and_held_work_deadlines_have_finite_owned_results()
    {
        await using var fixture = await OpenAsync();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        fixture.Controls.SetObserver("read.item", () => { entered.TrySetResult(); return new(release.Task); });
        var reads = new List<Task<MetadataResult<MetadataReadSnapshot>>>();
        try
        {
            reads.Add(fixture.Store.ReadAsync(new([Registry().Selector]), new(TimeSpan.FromMilliseconds(200)), default).AsTask());
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(10));
            for (var index = 0; index < 32; index++)
            { reads.Add(fixture.Store.ReadAsync(new([Registry().Selector]), new(), default).AsTask()); }
            Assert.Equal(MetadataFailureCode.Capacity, Failed(await fixture.Store.ReadAsync(new([Registry().Selector]), new(), default)));
            Assert.Equal(MetadataFailureCode.DeadlineExceeded, Failed(await reads[0]));
            Assert.Equal(MetadataFailureCode.Unavailable, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        }
        finally
        {
            release.TrySetResult();
            await Task.WhenAll(reads).WaitAsync(TimeSpan.FromSeconds(10));
            await fixture.WhenIdleAsync();
            fixture.Controls.RemoveObserver("read.item");
        }
        await Ticket(fixture);
    }

    [Fact]
    public async Task MP37_Disposal_owns_active_work_and_does_not_release_it_early()
    {
        var fixture = await OpenAsync();
        await using var barrier = new MetadataTestBarrier();
        fixture.Controls.SetObserver("M0", () => new(barrier.HoldAsync()));
        var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(Registry(), new ExpectedRevision.Absent()));
        var committing = fixture.Store.CommitAsync(batch, new(), default).AsTask();
        await barrier.Entered;
        var disposing = fixture.DisposeAsync().AsTask();
        try
        {
            Assert.False(disposing.IsCompleted);
            Assert.Equal(MetadataFailureCode.Disposed, Failed(await fixture.Store.ReserveOperationAsync(new(), default)));
        }
        finally { barrier.Release(); await committing; await disposing; }
    }

    [Fact]
    public async Task MP18_Known_exception_types_after_commit_attempt_are_still_uncertain()
    {
        await using var fixture = await OpenAsync();
        foreach (var exception in new Exception[] { new ArgumentException(MetadataTestData.Canary),
            new OverflowException(MetadataTestData.Canary), new IOException(MetadataTestData.Canary) })
        {
            var registry = Registry(exception is ArgumentException ? 11 : exception is OverflowException ? 12 : 13);
            var batch = Batch(await Ticket(fixture), new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent()));
            fixture.Controls.SetObserver("M1", () => throw exception);
            var result = await fixture.Store.CommitAsync(batch, new(), default);
            fixture.Controls.RemoveObserver("M1");
            Assert.Equal(MetadataFailureCode.Uncertain, Failed(result));
            Assert.Equal(batch.Ticket, Assert.IsType<MetadataOption<MetadataOperationTicket>.Some>(
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(result).Ticket).Value);
            Assert.IsType<MetadataResolution.Committed>(Success(await fixture.Store.ReconcileAsync(batch.Ticket, new(), default)));
            await Read<MetadataRegistry>(fixture, registry.Selector);
        }
    }
}
