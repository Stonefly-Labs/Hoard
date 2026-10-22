using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private async ValueTask<MetadataResult<MetadataSchemaAdmission>> UpgradeCoreAsync(MetadataSchemaRequest.Upgrade request, SqliteWorkBudget budget)
    {
        Volatile.Write(ref admitted, 0);
        if (targetVersion != V2 || request.ExpectedCurrent != V1 || request.Target != V2)
        { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.InvalidInput, MetadataPhase.Schema); }
        connection ??= Open(readOnly: false);
        var capture = VerifyCapture(request.VerifiedRecoveryPoint, budget);
        using (var schema = new SqliteStatement(Database, "SELECT version,epoch FROM metadata_schema WHERE singleton=1"))
        {
            if (!schema.Step() || schema.Text(0) != V1
                || new MetadataId(new Guid(schema.Bytes(1), bigEndian: true)) != capture.Point.Epoch)
            { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.InvalidInput, MetadataPhase.Schema); }
        }
        if (capture.Point.SchemaVersion != V1 || ChangeNumber(Database) != capture.ChangeNumber
            || LogicalDigest(Database, budget) != capture.Point.LogicalDigest
            || Exists("SELECT 1 FROM metadata_operations WHERE state=0 AND expires>?1 LIMIT 1",
                Math.Max(ReadTimeFloor(), clock.GetUtcNow().ToUnixTimeMilliseconds())))
        { return Fail<MetadataSchemaAdmission>(MetadataFailureCode.Conflict, MetadataPhase.Schema); }
        await observe("U0");
        budget.Check();
        Configure();
        await BeginAsync(budget);
        var newEpoch = new MetadataId(Guid.NewGuid());
        try
        {
            SqliteStatement.Execute(Database,
                "CREATE TABLE metadata_schema_next(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version TEXT NOT NULL,"
                + "epoch BLOB NOT NULL CHECK(length(epoch)=16),time_floor INTEGER NOT NULL CHECK(time_floor>=0),"
                + "change_number INTEGER NOT NULL CHECK(change_number>=0),recovery_annotation TEXT)");
            SqliteStatement.Execute(Database, "INSERT INTO metadata_schema_next(singleton,version,epoch,time_floor,change_number) "
                + "SELECT singleton,version,epoch,time_floor,change_number FROM metadata_schema");
            await observe("U1");
            budget.Check();
            SqliteStatement.Execute(Database, "DROP TABLE metadata_schema");
            SqliteStatement.Execute(Database, "ALTER TABLE metadata_schema_next RENAME TO metadata_schema");
            SqliteStatement.Execute(Database, "CREATE INDEX metadata_schema_recovery ON metadata_schema(recovery_annotation)");
            SqliteStatement.Execute(Database, "UPDATE metadata_schema SET version=?1,epoch=?2 WHERE singleton=1", V2, IdBytes(newEpoch));
            if (LogicalDigest(Database, budget) != capture.Point.LogicalDigest) { throw new SqliteNativeFailure(11); }
            await observe("U2");
            budget.Check();
            if (!budget.TryCommitDecision()) { budget.Check(); throw new SqliteBudgetFailure(false); }
            SqliteStatement.Execute(Database, "COMMIT");
            budget.Committed();
            await observe("U3");
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
        epoch = newEpoch;
        version = V2;
        budget.Check();
        Volatile.Write(ref admitted, 1);
        await observe("schema.admitted");
        return Ok(new MetadataSchemaAdmission(Provider, V2, newEpoch, true));
    }
}
