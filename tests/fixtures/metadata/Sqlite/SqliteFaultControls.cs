using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private int failNextWrite;
    public void InjectStorageCapacityForTest() => Interlocked.Exchange(ref failNextWrite, 1);

    public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutForTestAsync(bool partial) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            OwnStore();
            using var database = Open(readOnly: false);
            SqliteStatement.Execute(database, partial ? "CREATE TABLE metadata_schema(singleton INTEGER)" : "CREATE TABLE unrelated(value TEXT)");
            return ValueTask.FromResult(Ok(new MetadataId(Guid.NewGuid())));
        });

    public IDisposable HoldIndependentWriterForTest()
    {
        var independent = OpenFile(path, readOnly: false);
        try
        {
            SQLitePCL.raw.sqlite3_busy_timeout(independent.Handle, 0);
            SqliteStatement.Execute(independent, "BEGIN IMMEDIATE");
            return independent;
        }
        catch { independent.Dispose(); throw; }
    }

    public ValueTask<IAsyncDisposable> HoldIndependentWriterForTestAsync(CancellationToken cancellationToken) =>
        worker.HoldIndependentAsync(async () =>
        {
            await observe("writer.independent");
            return HoldIndependentWriterForTest();
        }, cancellationToken);

    public ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotForTestAsync(
        MetadataReadGroup request, CancellationToken cancellationToken)
    {
        if (Volatile.Read(ref disposed) != 0)
        { return ValueTask.FromResult(Fail<MetadataReadSnapshot>(MetadataFailureCode.Disposed, MetadataPhase.Read)); }
        if (Volatile.Read(ref admitted) == 0)
        { return ValueTask.FromResult(Fail<MetadataReadSnapshot>(MetadataFailureCode.IncompatibleSchema, MetadataPhase.Read)); }
        return worker.SubmitIndependent(cancellationToken, async budget =>
        {
            await observe("read.independent");
            budget.Check();
            var snapshot = ObserveCommittedSnapshot(request);
            budget.Check();
            return Ok(snapshot);
        });
    }

    public void StallNativeCallForTest(Action entered)
    {
        Database.CreateFunction<int>("hoard_fixture_hold", () =>
        {
            entered();
            Thread.Sleep(TimeSpan.FromMinutes(5));
            throw new TimeoutException("Parent did not terminate the native-call child.");
        });
        using var statement = new SqliteStatement(Database, "SELECT hoard_fixture_hold()");
        _ = statement.Step();
    }

    public ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationForTestAsync(CanonicalText resource, long generation) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            var lease = Get(new MetadataSelector.Lease(resource)) as MetadataWorkLease
                ?? throw new InvalidOperationException("Missing synthetic lease.");
            Put(lease with { Generation = generation });
            return ValueTask.FromResult(Ok(epoch!));
        });

    public ValueTask<MetadataResult<MetadataId>> FillLedgerForTestAsync() =>
        worker.Submit(TimeSpan.FromSeconds(30), default, MetadataPhase.Reserve, null, async budget =>
        {
            await BeginAsync(budget);
            try
            {
                var now = EffectiveNow();
                using var count = new SqliteStatement(Database, "SELECT count(*) FROM metadata_operations");
                if (!count.Step()) { throw new SqliteNativeFailure(11); }
                var initial = count.Number(0);
                count.Dispose();
                for (var index = initial; index < 100000; index++)
                {
                    budget.Check();
                    SqliteStatement.Execute(Database, "INSERT INTO metadata_operations(id,epoch,issued,expires,state) VALUES(?1,?2,?3,?4,0)",
                        Guid.NewGuid().ToByteArray(bigEndian: true), IdBytes(epoch!), now, checked(now + 86400000));
                }
                SqliteStatement.Execute(Database, "COMMIT");
                return Ok(epoch!);
            }
            finally
            {
                if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
            }
        });

    public ValueTask<MetadataResult<MetadataId>> CorruptRecordForTestAsync(MetadataSelector selector) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            SqliteStatement.Execute(Database, "UPDATE metadata_records SET payload=?1 WHERE key=?2", "{", RecordKey(selector));
            return ValueTask.FromResult(Ok(epoch!));
        });

    public ValueTask<MetadataResult<MetadataId>> MakeFutureSchemaForTestAsync() =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            Volatile.Write(ref admitted, 0);
            SqliteStatement.Execute(Database, "UPDATE metadata_schema SET version=?1 WHERE singleton=1", "fixture-sqlite-v999");
            return ValueTask.FromResult(Ok(epoch!));
        });

    public MetadataReadSnapshot ObserveCommittedSnapshot(MetadataReadGroup request)
    {
        _ = MetadataEncoding.Encode(request);
        using var independent = OpenFile(path, readOnly: true);
        SqliteStatement.Execute(independent, "BEGIN");
        try
        {
            var result = new MetadataReadSnapshot(request.Selectors.Select(selector => Get(selector, independent) is { } record
                ? (MetadataReadItem)new MetadataReadItem.Found(record) : new MetadataReadItem.NotFound(selector)).ToImmutableArray());
            _ = MetadataEncoding.Encode(result);
            SqliteStatement.Execute(independent, "COMMIT");
            return result;
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(independent.Handle) == 0) { SqliteStatement.Execute(independent, "ROLLBACK"); }
        }
    }
}
