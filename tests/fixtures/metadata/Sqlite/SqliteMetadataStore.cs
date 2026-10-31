using System.Collections.Immutable;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore : IMetadataStore, IMetadataSchemaAdministration
{
    private readonly string path;
    private readonly IMetadataPublicationAuthority authority;
    private readonly TimeProvider clock;
    private readonly Func<string, ValueTask> observe;
    private readonly Action<string> diagnostic;
    private readonly SqliteWorker worker;
    private SqliteConnection? connection;
    private FileStream? ownership;
    private int admitted;
    private int disposed;
    private MetadataId? epoch;
    private string version = "";
    private const string V1 = "fixture-sqlite-v1";
    private const string V2 = "fixture-sqlite-v2";
    private const string Provider = "fixture.metadata.sqlite";
    private readonly string targetVersion;
    private static readonly JsonSerializerOptions Json = new()
    { UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow };

    public SqliteMetadataStore(string databasePath, IMetadataPublicationAuthority publicationAuthority,
        TimeProvider timeProvider, Func<string, ValueTask> observer, Action<string> safeDiagnostic,
        string compatibleSchema = V2)
    {
        ArgumentNullException.ThrowIfNull(publicationAuthority);
        ArgumentNullException.ThrowIfNull(timeProvider);
        ArgumentNullException.ThrowIfNull(observer);
        ArgumentNullException.ThrowIfNull(safeDiagnostic);
        path = Path.GetFullPath(databasePath);
        if (compatibleSchema is not V1 and not V2) { throw new ArgumentException("Unsupported fixture application schema."); }
        targetVersion = compatibleSchema;
        authority = publicationAuthority;
        clock = timeProvider;
        observe = observer;
        diagnostic = safeDiagnostic;
        worker = new(CleanupAsync, diagnostic);
    }

    public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(
        MetadataCallOptions options, CancellationToken cancellationToken) =>
        Call(options, cancellationToken, MetadataPhase.Reserve, null, ReserveCoreAsync);

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(
        MetadataReadGroup request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Call(options, cancellationToken, MetadataPhase.Read, null, budget => ReadCoreAsync(request, budget));

    public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(
        MetadataPageQuery request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Call(options, cancellationToken, MetadataPhase.Page, null, budget => ReadPageCoreAsync(request, budget));

    public ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(
        MetadataMutationBatch request, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Call(options, cancellationToken, MetadataPhase.Commit, request?.Ticket, budget => CommitCoreAsync(request!, budget));

    public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(
        MetadataOperationTicket ticket, MetadataCallOptions options, CancellationToken cancellationToken) =>
        Call(options, cancellationToken, MetadataPhase.Reconcile, ticket, budget => ReconcileCoreAsync(ticket, budget));

    public ValueTask<MetadataResult<MetadataSchemaInspection>> InspectAsync(
        MetadataAdministrationOptions options, CancellationToken cancellationToken) =>
        Admin(options, cancellationToken, budget => InspectCoreAsync(budget));

    public ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareAsync(
        MetadataSchemaRequest request, MetadataAdministrationOptions options, CancellationToken cancellationToken) =>
        Admin(options, cancellationToken, budget => PrepareCoreAsync(request, budget));

    private ValueTask<MetadataResult<T>> Call<T>(MetadataCallOptions options, CancellationToken token,
        MetadataPhase phase, MetadataOperationTicket? ticket, Func<SqliteWorkBudget, ValueTask<MetadataResult<T>>> action) where T : notnull
    {
        if (options is null || options.EffectiveTimeout < TimeSpan.FromMilliseconds(1) || options.EffectiveTimeout > TimeSpan.FromSeconds(30))
        { return ValueTask.FromResult(SqliteWorker.Failure<T>(MetadataFailureCode.InvalidInput, phase)); }
        if (Volatile.Read(ref disposed) != 0) { return ValueTask.FromResult(SqliteWorker.Failure<T>(MetadataFailureCode.Disposed, phase)); }
        if (Volatile.Read(ref admitted) == 0) { return ValueTask.FromResult(SqliteWorker.Failure<T>(MetadataFailureCode.IncompatibleSchema, phase)); }
        return worker.Submit(options.EffectiveTimeout, token, phase, ticket, action);
    }

    private ValueTask<MetadataResult<T>> Admin<T>(MetadataAdministrationOptions options, CancellationToken token,
        Func<SqliteWorkBudget, ValueTask<MetadataResult<T>>> action) where T : notnull
    {
        if (options is null || options.EffectiveTimeout < TimeSpan.FromMilliseconds(1) || options.EffectiveTimeout > TimeSpan.FromMinutes(2))
        { return ValueTask.FromResult(SqliteWorker.Failure<T>(MetadataFailureCode.InvalidInput, MetadataPhase.Schema)); }
        if (Volatile.Read(ref disposed) != 0) { return ValueTask.FromResult(SqliteWorker.Failure<T>(MetadataFailureCode.Disposed, MetadataPhase.Schema)); }
        return worker.Submit(options.EffectiveTimeout, token, MetadataPhase.Schema, null, action);
    }

    private SqliteConnection Database => connection ?? throw new InvalidOperationException("Metadata store not admitted.");
    private static byte[] IdBytes(MetadataId value) => value.Value.ToByteArray(bigEndian: true);
    private static byte[] RecordKey(MetadataSelector value) => MetadataEncoding.Key(value).ToArray();
    private static MetadataRevision NewRevision() => new(Guid.NewGuid());
    private static MetadataResult<T> Ok<T>(T value) where T : notnull => new MetadataResult<T>.Success(value);
    private static MetadataResult<T> Fail<T>(MetadataFailureCode code, MetadataPhase phase) where T : notnull => SqliteWorker.Failure<T>(code, phase);

    private async ValueTask BeginAsync(SqliteWorkBudget budget)
    {
        while (true)
        {
            budget.Check();
            try { SqliteStatement.Execute(Database, "BEGIN IMMEDIATE"); return; }
            catch (SqliteNativeFailure error) when (error.Code is 5 or 6)
            { await Task.Delay(budget.Remaining < TimeSpan.FromMilliseconds(50) ? budget.Remaining : TimeSpan.FromMilliseconds(50)); }
        }
    }

    private long EffectiveNow()
    {
        using var select = new SqliteStatement(Database, "SELECT time_floor FROM metadata_schema WHERE singleton=1");
        if (!select.Step()) { throw new SqliteNativeFailure(11); }
        var now = Math.Max(clock.GetUtcNow().ToUnixTimeMilliseconds(), select.Number(0));
        _ = new MetadataInstant(now);
        SqliteStatement.Execute(Database, "UPDATE metadata_schema SET time_floor=?1 WHERE singleton=1", now);
        return now;
    }

    private MetadataRecord? Get(MetadataSelector selector, SqliteConnection? database = null)
    {
        var key = RecordKey(selector);
        using var select = new SqliteStatement(database ?? Database, "SELECT length(CAST(payload AS BLOB)),payload FROM metadata_records WHERE key=?1", key);
        if (!select.Step()) { return null; }
        if (select.Number(0) > MetadataEncoding.MaximumBytes) { throw new SqliteNativeFailure(11); }
        return DecodeRecord(select.Text(1), key);
    }

    private static MetadataRecord DecodeRecord(string text, ReadOnlySpan<byte> key)
    {
        if (Encoding.UTF8.GetByteCount(text) > MetadataEncoding.MaximumBytes) { throw new SqliteNativeFailure(11); }
        try
        {
            var record = JsonSerializer.Deserialize<MetadataRecord>(text, Json) ?? throw new SqliteNativeFailure(11);
            MetadataEncoding.Validate(record);
            if (!RecordKey(record.Selector).AsSpan().SequenceEqual(key)) { throw new SqliteNativeFailure(11); }
            return record;
        }
        catch (ArgumentException) { throw new SqliteNativeFailure(11); }
        catch (JsonException) { throw new SqliteNativeFailure(11); }
    }

    private void Put(MetadataRecord record)
    {
        MetadataEncoding.Validate(record);
        var indexes = IndexValues(record);
        var key = RecordKey(record.Selector);
        SqliteStatement.Execute(Database,
            "INSERT INTO metadata_records(key,kind,registry,package,policy,ecosystem,payload) VALUES(?1,?2,?3,?4,?5,?6,?7) "
            + "ON CONFLICT(key) DO UPDATE SET registry=excluded.registry,package=excluded.package,policy=excluded.policy,"
            + "ecosystem=excluded.ecosystem,payload=excluded.payload",
            key, (int)key[0], indexes.Registry, indexes.Package, indexes.Policy, indexes.Ecosystem, JsonSerializer.Serialize(record, Json));
    }

    private bool Exists(string sql, params object?[] arguments)
    {
        using var select = new SqliteStatement(Database, sql, arguments);
        return select.Step();
    }

    private async ValueTask<MetadataResult<MetadataReadSnapshot>> ReadCoreAsync(MetadataReadGroup request, SqliteWorkBudget budget)
    {
        _ = MetadataEncoding.Encode(request);
        SqliteStatement.Execute(Database, "BEGIN");
        try
        {
            var items = ImmutableArray.CreateBuilder<MetadataReadItem>(request.Selectors.Length);
            foreach (var selector in request.Selectors)
            {
                budget.Check();
                items.Add(Get(selector) is { } record ? new MetadataReadItem.Found(record) : new MetadataReadItem.NotFound(selector));
                await observe("read.item");
            }
            var snapshot = new MetadataReadSnapshot(items.MoveToImmutable());
            _ = MetadataEncoding.Encode(snapshot);
            budget.Check();
            SqliteStatement.Execute(Database, "COMMIT");
            return Ok(snapshot);
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
    }

    private ValueTask CleanupAsync()
    {
        Volatile.Write(ref admitted, 0);
        connection?.Dispose();
        connection = null;
        ownership?.Dispose();
        ownership = null;
        return ValueTask.CompletedTask;
    }

    public async ValueTask DisposeAsync()
    {
        Interlocked.Exchange(ref disposed, 1);
        Volatile.Write(ref admitted, 0);
        await worker.StopAsync();
    }

    public Task WhenIdleAsync() => worker.WhenIdleAsync();
    // Includes native handle cleanup; an idle but open worker has not settled its lifetime.
    public Task ObserveLifetimeSettlementForTest() => worker.ObserveLifetimeSettlementForTest();
}
