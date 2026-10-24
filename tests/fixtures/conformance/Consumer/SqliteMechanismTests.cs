using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Metadata.Sqlite;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Fixtures.Conformance.Consumer;

public sealed class SqliteMechanismTests
{
    [Fact]
    public async Task Raw_fingerprint_rejects_oversized_unindexed_native_rows_before_materialization()
    {
        await using var fixture = new StoreFixture(_ => ValueTask.CompletedTask);
        Success(await fixture.Store.CreateUnrecognizedLayoutForTestAsync(false));
        using (var connection = new Microsoft.Data.Sqlite.SqliteConnection(new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder
        { DataSource = fixture.DatabasePath, Pooling = false }.ConnectionString))
        {
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText = "ALTER TABLE unrelated ADD COLUMN extra BLOB; "
                + "INSERT INTO unrelated(value,extra) VALUES(zeroblob(1310720),zeroblob(1310720));";
            command.ExecuteNonQuery();
        }
        Assert.Equal(MetadataFailureCode.Capacity,
            Assert.IsType<MetadataResult<string>.Failure>(await fixture.Store.RawStateFingerprintForTestAsync(default)).Code);
        await fixture.Store.WhenIdleAsync();
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Raw_record_controls_preserve_damaged_bytes_and_restore_exact_committed_state(bool oversized)
    {
        await using var fixture = new StoreFixture(_ => ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var record = Registry();
        var ticket = Success(await store.ReserveOperationAsync(new(), default));
        Success(await store.CommitAsync(new(ticket, [new MetadataMutation.PutRegistry(record, new ExpectedRevision.Absent())],
            new MetadataOption<MetadataLeaseGuard>.None()), new(), default));
        var original = Success(await store.RecordPayloadForTestAsync(record.Selector));
        var before = Success(await store.RawStateFingerprintForTestAsync(default));
        var damaged = oversized ? new string(' ', MetadataEncoding.MaximumBytes) + original : "{synthetic";
        try
        {
            Success(await store.ReplaceRecordPayloadForTestAsync(record.Selector, damaged));
            var fingerprint = Success(await store.RawStateFingerprintForTestAsync(default));
            Assert.NotEqual(before, fingerprint);
            Assert.Equal(MetadataFailureCode.CorruptState,
                Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(
                    await store.ReadAsync(new([record.Selector]), new(), default)).Code);
            Assert.Equal(damaged, Success(await store.RecordPayloadForTestAsync(record.Selector)));
            Assert.Equal(fingerprint, Success(await store.RawStateFingerprintForTestAsync(default)));
        }
        finally { Success(await store.ReplaceRecordPayloadForTestAsync(record.Selector, original)); }
        Assert.Equal(before, Success(await store.RawStateFingerprintForTestAsync(default)));
        Assert.IsType<MetadataReadItem.Found>(Assert.Single(Success(
            await store.ReadAsync(new([record.Selector]), new(), default)).Items));
    }

    [Theory]
    [InlineData("short")]
    [InlineData("missing")]
    [InlineData("text")]
    [InlineData("fractional")]
    [InlineData("text-limit")]
    public async Task Raw_operation_controls_preserve_native_storage_types_and_restore_exact_replay(string damage)
    {
        await using var fixture = new StoreFixture(_ => ValueTask.CompletedTask);
        var store = fixture.Store;
        Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
        var record = Registry();
        var ticket = Success(await store.ReserveOperationAsync(new(), default));
        var batch = new MetadataMutationBatch(ticket, [new MetadataMutation.PutRegistry(record, new ExpectedRevision.Absent())],
            new MetadataOption<MetadataLeaseGuard>.None());
        var receipt = MetadataEncoding.Encode(Success(await store.CommitAsync(batch, new(), default)));
        var original = Success(await store.OperationImageForTestAsync(ticket));
        var before = Success(await store.RawStateFingerprintForTestAsync(default));
        var damaged = damage switch
        {
            "short" => original with { FingerprintHex = "aa" },
            "missing" => original with { FingerprintHex = null },
            "text" => original with { FingerprintHex = null, FingerprintText = new string('x', 32) },
            "fractional" => original with { State = 1.5 },
            "text-limit" => original with { FingerprintHex = null, FingerprintText = new string('\u0100', 128) },
            _ => throw new ArgumentException("BindingInvalid")
        };
        try
        {
            if (damage == "text-limit")
            {
                Assert.Equal(MetadataFailureCode.InvalidInput,
                    Assert.IsType<MetadataResult<MetadataId>.Failure>(
                        await store.ReplaceOperationImageForTestAsync(ticket, damaged)).Code);
                Assert.Equal(before, Success(await store.RawStateFingerprintForTestAsync(default)));
                return;
            }
            Success(await store.ReplaceOperationImageForTestAsync(ticket, damaged));
            var fingerprint = Success(await store.RawStateFingerprintForTestAsync(default));
            Assert.NotEqual(before, fingerprint);
            Assert.Equal(MetadataFailureCode.CorruptState,
                Assert.IsType<MetadataResult<MetadataResolution>.Failure>(
                    await store.ReconcileAsync(ticket, new(), default)).Code);
            Assert.Equal(MetadataFailureCode.CorruptState,
                Assert.IsType<MetadataResult<MetadataCommitReceipt>.Failure>(
                    await store.CommitAsync(batch, new(), default)).Code);
            Assert.Equal(damaged, Success(await store.OperationImageForTestAsync(ticket)));
            Assert.Equal(fingerprint, Success(await store.RawStateFingerprintForTestAsync(default)));
        }
        finally { Success(await store.ReplaceOperationImageForTestAsync(ticket, original)); }
        Assert.Equal(before, Success(await store.RawStateFingerprintForTestAsync(default)));
        Assert.Equal<byte>(receipt, MetadataEncoding.Encode(Success(await store.CommitAsync(batch, new(), default))));
    }

    [Theory]
    [InlineData("empty")]
    [InlineData("unrecognized")]
    [InlineData("partial")]
    [InlineData("future")]
    public async Task Raw_fingerprint_observes_rejected_layouts_without_admitting_or_repairing_them(string layout)
    {
        await using var fixture = new StoreFixture(_ => ValueTask.CompletedTask);
        var store = fixture.Store;
        if (layout is "unrecognized" or "partial")
        { Success(await store.CreateUnrecognizedLayoutForTestAsync(layout == "partial")); }
        if (layout == "future")
        {
            Success(await store.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
            Success(await store.MakeFutureSchemaForTestAsync());
        }
        var before = Success(await store.RawStateFingerprintForTestAsync(default));
        Assert.Equal(64, before.Length);
        Success(await store.InspectAsync(new(), default));
        Assert.Equal(MetadataFailureCode.IncompatibleSchema,
            Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Failure>(await store.PrepareAsync(
                new MetadataSchemaRequest.InspectOnly(), new(), default)).Code);
        Assert.Equal(before, Success(await store.RawStateFingerprintForTestAsync(default)));
    }

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

    private static MetadataRegistry Registry() => new()
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
            Store = new(DatabasePath, new RejectingAuthority(),
                new MetadataConformanceClock(new(1_800_000_000_000)), observer,
                _ => throw new InvalidOperationException("UnexpectedDiagnostic"));
        }
        public SqliteMetadataStore Store { get; }
        public string DatabasePath => Path.Combine(directory, "metadata.db");
        public async ValueTask DisposeAsync()
        {
            await Store.DisposeAsync();
            foreach (var file in Directory.GetFiles(directory)) { File.Delete(file); }
            Directory.Delete(directory);
        }
    }
}
