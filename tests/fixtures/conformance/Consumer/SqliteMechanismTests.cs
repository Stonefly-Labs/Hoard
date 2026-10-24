using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class SqliteMechanismTests
{
    [Fact]
    public async Task Cancelled_writer_acquisition_keeps_late_native_handles_owned_until_they_close()
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var fixture = new StoreFixture(point => point == "writer.independent" ? Hold() : ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        using var cancellation = new CancellationTokenSource();
        var acquiring = store.HoldIndependentWriterForTestAsync(cancellation.Token).AsTask();
        Task? disposing = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            cancellation.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(async () => await acquiring);
            disposing = store.DisposeAsync().AsTask();
            Assert.False(disposing.IsCompleted);
            Assert.False(store.ObserveLifetimeSettlementForTest().IsCompleted);
        }
        finally
        {
            release.TrySetResult();
            if (disposing is not null) { await disposing.WaitAsync(TimeSpan.FromSeconds(10)); }
            var error = await Record.ExceptionAsync(async () =>
            {
                if (await acquiring is { } writer) { await writer.DisposeAsync(); }
            });
            Assert.True(error is null or OperationCanceledException);
        }
        Assert.True(store.ObserveLifetimeSettlementForTest().IsCompletedSuccessfully);

        async ValueTask Hold()
        {
            entered.TrySetResult();
            await release.Task.WaitAsync(TimeSpan.FromSeconds(15));
        }
    }

    [Fact]
    public async Task Cancelled_independent_read_does_not_release_the_underlying_work()
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var fixture = new StoreFixture(point => point == "read.independent" ? Hold() : ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        using var cancellation = new CancellationTokenSource();
        var reading = store.ObserveIndependentSnapshotForTestAsync(
            new([new MetadataSelector.Registry(new(Guid.NewGuid()))]), cancellation.Token).AsTask();
        Task? disposing = null;
        Task? idle = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            cancellation.Cancel();
            Assert.Equal(MetadataFailureCode.CancelledBeforeCommit,
                Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(await reading).Code);
            idle = store.WhenIdleAsync();
            disposing = store.DisposeAsync().AsTask();
            Assert.False(idle.IsCompleted);
            Assert.False(disposing.IsCompleted);
            Assert.False(store.ObserveLifetimeSettlementForTest().IsCompleted);
        }
        finally
        {
            release.TrySetResult();
            await Task.WhenAll(reading, idle ?? Task.CompletedTask, disposing ?? Task.CompletedTask)
                .WaitAsync(TimeSpan.FromSeconds(10));
        }
        Assert.True(store.ObserveLifetimeSettlementForTest().IsCompletedSuccessfully);

        async ValueTask Hold()
        {
            entered.TrySetResult();
            await release.Task.WaitAsync(TimeSpan.FromSeconds(15));
        }
    }

    [Fact]
    public async Task Independent_diagnostic_failure_is_surfaced_and_faults_the_actual_lifetime()
    {
        var directory = Directory.CreateTempSubdirectory("hoard-sqlite-diagnostic-").FullName;
        var path = Path.Combine(directory, "metadata.db");
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var store = new SqliteMetadataStore(path, new RejectingAuthority(), clock,
            point => point == "read.independent" ? throw new InvalidOperationException("SyntheticObserverFailure") : ValueTask.CompletedTask,
            _ => throw new InvalidOperationException("SyntheticDiagnosticFailure"));
        try
        {
            Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            var error = await Assert.ThrowsAsync<InvalidOperationException>(async () =>
                await store.ObserveIndependentSnapshotForTestAsync(
                    new([new MetadataSelector.Registry(new(Guid.NewGuid()))]), default));
            Assert.Equal("SyntheticDiagnosticFailure", error.Message);
            var cleanup = await Assert.ThrowsAsync<InvalidOperationException>(async () => await store.DisposeAsync());
            Assert.Equal("CleanupIncomplete", cleanup.Message);
            Assert.True(store.ObserveLifetimeSettlementForTest().IsFaulted);
            await using var reopened = new SqliteMetadataStore(path, new RejectingAuthority(), clock,
                _ => ValueTask.CompletedTask, _ => throw new InvalidOperationException("UnexpectedDiagnostic"));
            Success(await reopened.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
        }
        finally
        {
            await Record.ExceptionAsync(async () => await store.DisposeAsync());
            if (!store.ObserveLifetimeSettlementForTest().IsCompleted)
            { throw new InvalidOperationException("CleanupIncomplete"); }
            foreach (var file in Directory.GetFiles(directory)) { File.Delete(file); }
            Directory.Delete(directory);
        }
    }

    [Fact]
    public async Task Independent_read_work_is_included_in_idle_and_actual_worker_termination()
    {
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await using var fixture = new StoreFixture(point => point == "read.independent" ? Hold() : ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var reading = store.ObserveIndependentSnapshotForTestAsync(
            new([new MetadataSelector.Registry(new(Guid.NewGuid()))]), default).AsTask();
        Task? disposing = null;
        Task? idle = null;
        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            idle = store.WhenIdleAsync();
            Assert.False(idle.IsCompleted);
            disposing = store.DisposeAsync().AsTask();
            Assert.False(disposing.IsCompleted);
            Assert.False(store.ObserveLifetimeSettlementForTest().IsCompleted);
        }
        finally
        {
            release.TrySetResult();
            await Task.WhenAll(reading, idle ?? Task.CompletedTask, disposing ?? Task.CompletedTask)
                .WaitAsync(TimeSpan.FromSeconds(10));
        }
        Assert.IsType<MetadataReadItem.NotFound>(Assert.Single(Success(await reading).Items));
        Assert.True(store.ObserveLifetimeSettlementForTest().IsCompletedSuccessfully);

        async ValueTask Hold()
        {
            entered.TrySetResult();
            await release.Task.WaitAsync(TimeSpan.FromSeconds(15));
        }
    }

    [Fact]
    public async Task Independent_writer_lease_is_not_ordinary_work_but_closes_before_lifetime_settlement()
    {
        await using var fixture = new StoreFixture(_ => ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        await using var writer = await store.HoldIndependentWriterForTestAsync(default);
        await store.WhenIdleAsync().WaitAsync(TimeSpan.FromSeconds(1));
        Assert.False(store.ObserveLifetimeSettlementForTest().IsCompleted);
        await store.DisposeAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(10));
        Assert.True(store.ObserveLifetimeSettlementForTest().IsCompletedSuccessfully);
        await writer.DisposeAsync();
    }

    [Fact]
    public async Task Genuine_worker_termination_outlives_public_deadline_and_includes_native_handle_cleanup()
    {
        var directory = Directory.CreateTempSubdirectory("hoard-sqlite-settlement-").FullName;
        var path = Path.Combine(directory, "metadata.db");
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var clock = new MetadataConformanceClock(new(1_800_000_000_000));
        var store = new SqliteMetadataStore(path, new RejectingAuthority(), clock,
            point => point == "M0" ? Hold() : ValueTask.CompletedTask,
            _ => throw new InvalidOperationException("UnexpectedDiagnostic"));
        Task<MetadataResult<MetadataCommitReceipt>>? committing = null;
        Task? disposing = null;
        Task? actual = null;
        try
        {
            Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            var ticket = Success(await store.ReserveOperationAsync(new(), default));
            var registry = new MetadataRegistry
            {
                Id = new(Guid.NewGuid()),
                Ecosystem = new("nuget"),
                Upstream = new("https://example.invalid/v3/"),
                Enabled = true,
                Label = new("synthetic"),
                PolicyId = new MetadataOption<MetadataId>.None(),
                Secret = new MetadataOption<MetadataSecretReference>.None(),
                Revision = new(Guid.NewGuid())
            };
            committing = store.CommitAsync(new(ticket,
                [new MetadataMutation.PutRegistry(registry, new ExpectedRevision.Absent())],
                new MetadataOption<MetadataLeaseGuard>.None()), new(TimeSpan.FromMilliseconds(200)), default).AsTask();
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            actual = store.ObserveLifetimeSettlementForTest();
            Assert.Equal(MetadataFailureCode.DeadlineExceeded,
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(await committing).Code);
            Assert.False(actual.IsCompleted);
            disposing = store.DisposeAsync().AsTask();
            Assert.Same(actual, store.ObserveLifetimeSettlementForTest());
            Assert.False(actual.IsCompleted);
            await using (var competing = NewStore())
            {
                Assert.Equal(MetadataFailureCode.Unavailable,
                    Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await competing.PrepareAsync(
                        new MetadataSchemaRequest.InspectOnly(), new(), default)).Code);
            }
            release.TrySetResult();
            await Task.WhenAll(disposing, actual).WaitAsync(TimeSpan.FromSeconds(10));
            Assert.True(actual.IsCompletedSuccessfully);
            await using var reopened = NewStore();
            Success(await reopened.PrepareAsync(new MetadataSchemaRequest.InspectOnly(), new(), default));
        }
        finally
        {
            release.TrySetResult();
            try
            {
                await Task.WhenAll(committing ?? Task.CompletedTask, disposing ?? Task.CompletedTask,
                    actual ?? Task.CompletedTask).WaitAsync(TimeSpan.FromSeconds(10));
            }
            finally
            {
                await store.DisposeAsync();
                foreach (var file in Directory.GetFiles(directory)) { File.Delete(file); }
                Directory.Delete(directory);
            }
        }

        async ValueTask Hold()
        {
            entered.TrySetResult();
            await release.Task.WaitAsync(TimeSpan.FromSeconds(15));
        }
        SqliteMetadataStore NewStore() => new(path, new RejectingAuthority(), clock,
            _ => ValueTask.CompletedTask, _ => throw new InvalidOperationException("UnexpectedDiagnostic"));
    }

    private static T Success<T>(MetadataResult<T> result) where T : notnull =>
        Assert.IsType<MetadataResult<T>.Success>(result).Value;

    private sealed class RejectingAuthority : IMetadataPublicationAuthority
    {
        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(
            MetadataArtifactEvidence evidence, MetadataCallOptions options, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("UnexpectedPublication");
    }

    private sealed class StoreFixture : IAsyncDisposable
    {
        private readonly string directory = Directory.CreateTempSubdirectory("hoard-sqlite-auxiliary-").FullName;
        public StoreFixture(Func<string, ValueTask> observer)
        {
            Store = new(Path.Combine(directory, "metadata.db"), new RejectingAuthority(),
                new MetadataConformanceClock(new(1_800_000_000_000)), observer,
                _ => throw new InvalidOperationException("UnexpectedDiagnostic"));
        }
        public SqliteMetadataStore Store { get; }
        public async ValueTask DisposeAsync()
        {
            await Store.DisposeAsync();
            foreach (var file in Directory.GetFiles(directory)) { File.Delete(file); }
            Directory.Delete(directory);
        }
    }
}
