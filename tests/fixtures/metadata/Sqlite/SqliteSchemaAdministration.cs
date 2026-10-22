using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private void OwnStore()
    {
        ownership ??= new FileStream(path + ".owner", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
    }

    private SqliteConnection Open(bool readOnly)
    {
        var database = new SqliteConnection(new SqliteConnectionStringBuilder
        {
            DataSource = path,
            Mode = readOnly ? SqliteOpenMode.ReadOnly : SqliteOpenMode.ReadWriteCreate,
            Pooling = false,
            DefaultTimeout = 1
        }.ConnectionString);
        try { database.Open(); return database; }
        catch { database.Dispose(); throw; }
    }

    private async ValueTask<MetadataResult<MetadataSchemaInspection>> InspectCoreAsync(SqliteWorkBudget budget)
    {
        await observe("schema.inspect");
        budget.Check();
        OwnStore();
        if (!File.Exists(path)) { return Ok(new MetadataSchemaInspection(MetadataSchemaState.Empty, Provider, "", targetVersion, MetadataSchemaAction.CreateExplicitly)); }
        using var database = Open(readOnly: true);
        var names = new HashSet<string>(StringComparer.Ordinal);
        using (var schema = new SqliteStatement(database, "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND type IN('table','view')"))
        { while (schema.Step()) { budget.Check(); names.Add(schema.Text(0)); } }
        if (names.Count == 0) { return Ok(new MetadataSchemaInspection(MetadataSchemaState.Empty, Provider, "", targetVersion, MetadataSchemaAction.CreateExplicitly)); }
        if (!names.SetEquals(["metadata_schema", "metadata_records", "metadata_edges", "metadata_operations"]))
        { return Ok(new MetadataSchemaInspection(MetadataSchemaState.Incompatible, Provider, "", V2, MetadataSchemaAction.UseCompatibleApplication)); }
        string observed;
        try
        {
            using var schema = new SqliteStatement(database, "SELECT version,epoch,time_floor,change_number FROM metadata_schema WHERE singleton=1");
            if (!schema.Step()) { throw new SqliteNativeFailure(11); }
            observed = schema.Text(0);
            if (observed is not V1 and not V2 || targetVersion == V1 && observed != V1)
            { return Ok(new MetadataSchemaInspection(MetadataSchemaState.Incompatible, Provider, "unsupported", V2, MetadataSchemaAction.UseCompatibleApplication)); }
            if (schema.Bytes(1).Length != 16 || schema.Number(2) < 0 || schema.Number(3) < 0 || schema.Step())
            { throw new SqliteNativeFailure(11); }
            using var integrity = new SqliteStatement(database, "PRAGMA quick_check");
            if (!integrity.Step() || integrity.Text(0) != "ok" || integrity.Step()) { throw new SqliteNativeFailure(11); }
            using var foreignKeys = new SqliteStatement(database, "PRAGMA foreign_key_check");
            if (foreignKeys.Step()) { throw new SqliteNativeFailure(11); }
            foreach (var table in new[] { "metadata_records", "metadata_operations", "metadata_edges" })
            {
                using var select = new SqliteStatement(database, $"SELECT count(*) FROM {table}");
                if (!select.Step() || select.Number(0) < 0) { throw new SqliteNativeFailure(11); }
            }
            VerifyLayout(database, observed, budget);
            VerifyLogicalIntegrity(database, budget);
        }
        catch (SqliteNativeFailure error) when (error.Code == 1)
        { return Ok(new MetadataSchemaInspection(MetadataSchemaState.Incompatible, Provider, "", V2, MetadataSchemaAction.UseCompatibleApplication)); }
        budget.Check();
        return Ok(new MetadataSchemaInspection(observed == targetVersion ? MetadataSchemaState.Compatible : MetadataSchemaState.UpgradeRequired,
            Provider, observed, targetVersion, observed == targetVersion ? MetadataSchemaAction.Admit : MetadataSchemaAction.UpgradeWithRecoveryPoint));
    }

    private async ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareCoreAsync(MetadataSchemaRequest request, SqliteWorkBudget budget)
    {
        MetadataEncoding.Validate(request);
        var result = await InspectCoreAsync(budget);
        if (result is MetadataResult<MetadataSchemaInspection>.Failure failure)
        { return Fail<MetadataSchemaAdmission>(failure.Code, MetadataPhase.Schema); }
        var inspection = ((MetadataResult<MetadataSchemaInspection>.Success)result).Value;
        if (inspection.State == MetadataSchemaState.Incompatible)
        { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.IncompatibleSchema, MetadataPhase.Schema); }
        if (inspection.State == MetadataSchemaState.UpgradeRequired)
        {
            if (request is not MetadataSchemaRequest.Upgrade upgrade)
            { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.IncompatibleSchema, MetadataPhase.Schema); }
            return await UpgradeCoreAsync(upgrade, budget);
        }
        if (request is MetadataSchemaRequest.Upgrade)
        { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.InvalidInput, MetadataPhase.Schema); }
        if (inspection.State == MetadataSchemaState.Empty && request is not MetadataSchemaRequest.CreateIfEmpty)
        { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.IncompatibleSchema, MetadataPhase.Schema); }
        connection ??= Open(readOnly: false);
        Configure();
        if (inspection.State == MetadataSchemaState.Empty)
        {
            await BeginAsync(budget);
            try
            {
                using var resource = typeof(SqliteMetadataStore).Assembly.GetManifestResourceStream(
                    "Hoard.Fixtures.Metadata.Sqlite." + (targetVersion == V1 ? "SchemaV1.sql" : "SchemaV2.sql"))
                    ?? throw new InvalidOperationException("Missing private fixture schema.");
                using var reader = new StreamReader(resource);
                foreach (var sql in (await reader.ReadToEndAsync()).Split(';', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries))
                { budget.Check(); SqliteStatement.Execute(Database, sql); }
                epoch = new(Guid.NewGuid());
                SqliteStatement.Execute(Database, "INSERT INTO metadata_schema(singleton,version,epoch,time_floor,change_number) VALUES(1,?1,?2,0,0)", targetVersion, IdBytes(epoch));
                budget.Check();
                if (!budget.TryCommitDecision()) { throw new SqliteBudgetFailure(budget.Cancelled); }
                SqliteStatement.Execute(Database, "COMMIT");
                budget.Committed();
            }
            finally
            {
                if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
            }
        }
        using (var schema = new SqliteStatement(Database, "SELECT version,epoch FROM metadata_schema WHERE singleton=1"))
        {
            if (!schema.Step()) { throw new SqliteNativeFailure(11); }
            version = schema.Text(0);
            epoch = new(new Guid(schema.Bytes(1), bigEndian: true));
        }
        budget.Check();
        Volatile.Write(ref admitted, 1);
        await observe("schema.admitted");
        return Ok(new MetadataSchemaAdmission(Provider, version, epoch, true));
    }

    private void Configure()
    {
        using (var journal = new SqliteStatement(Database, "PRAGMA journal_mode=WAL"))
        {
            if (!journal.Step() || journal.Text(0) != "wal" || journal.Step()) { throw new SqliteNativeFailure(1); }
        }
        SqliteStatement.Execute(Database, "PRAGMA synchronous=FULL");
        SqliteStatement.Execute(Database, "PRAGMA foreign_keys=ON");
        if (SQLitePCL.raw.sqlite3_busy_timeout(Database.Handle, 0) != SQLitePCL.raw.SQLITE_OK)
        { throw new SqliteNativeFailure(1); }
        foreach (var setting in new[] { ("synchronous", 2L), ("foreign_keys", 1L), ("busy_timeout", 0L) })
        {
            using var check = new SqliteStatement(Database, "PRAGMA " + setting.Item1);
            if (!check.Step() || check.Number(0) != setting.Item2) { throw new SqliteNativeFailure(1); }
        }
    }
}
