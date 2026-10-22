using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private sealed record Capture(MetadataRecoveryPoint Point, long ChangeNumber, string FileDigest);
    private string CaptureDirectory => path + ".captures";
    private string CapturePath(MetadataId id) => Path.Combine(CaptureDirectory, id.Value.ToString("N") + ".db");

    public ValueTask<MetadataResult<MetadataRecoveryPoint>> CaptureRecoveryPointAsync(
        MetadataAdministrationOptions options, CancellationToken cancellationToken)
    {
        if (options is null || options.EffectiveTimeout < TimeSpan.FromMilliseconds(1) || options.EffectiveTimeout > TimeSpan.FromMinutes(2))
        { return ValueTask.FromResult(Fail<MetadataRecoveryPoint>(MetadataFailureCode.InvalidInput, MetadataPhase.Schema)); }
        Volatile.Write(ref admitted, 0);
        return Admin(options, cancellationToken, CaptureCoreAsync);
    }

    private async ValueTask<MetadataResult<MetadataRecoveryPoint>> CaptureCoreAsync(SqliteWorkBudget budget)
    {
        OwnStore();
        var inspection = await InspectCoreAsync(budget);
        if (inspection is not MetadataResult<MetadataSchemaInspection>.Success { Value.State: MetadataSchemaState.Compatible or MetadataSchemaState.UpgradeRequired })
        { return Fail<MetadataRecoveryPoint>(MetadataFailureCode.IncompatibleSchema, MetadataPhase.Schema); }
        connection ??= Open(readOnly: false);
        {
            using var schema = new SqliteStatement(Database, "SELECT version,epoch FROM metadata_schema WHERE singleton=1");
            if (!schema.Step()) { throw new SqliteNativeFailure(11); }
            version = schema.Text(0);
            epoch = new(new Guid(schema.Bytes(1), bigEndian: true));
        }
        Configure();
        await BeginAsync(budget);
        long change;
        string logical;
        try
        {
            var now = EffectiveNow();
            if (Exists("SELECT 1 FROM metadata_operations WHERE state=0 AND expires>?1 LIMIT 1", now))
            { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
            change = ChangeNumber(Database);
            logical = LogicalDigest(Database, budget);
            SqliteStatement.Execute(Database, "COMMIT");
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
        var id = new MetadataId(Guid.NewGuid());
        Directory.CreateDirectory(CaptureDirectory);
        if (!OperatingSystem.IsWindows()) { File.SetUnixFileMode(CaptureDirectory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute); }
        var destination = CapturePath(id);
        await observe("backup.before_native");
        budget.Check();
        using (var backup = new SqliteConnection(new SqliteConnectionStringBuilder
        { DataSource = destination, Pooling = false, Mode = SqliteOpenMode.ReadWriteCreate }.ConnectionString))
        {
            backup.Open();
            Database.BackupDatabase(backup);
        }
        await observe("backup.after_native");
        budget.Check();
        using (var verify = OpenFile(destination, readOnly: true))
        {
            VerifyLayout(verify, version, budget);
            VerifyLogicalIntegrity(verify, budget);
            if (LogicalDigest(verify, budget) != logical || ChangeNumber(verify) != change)
            { throw new SqliteNativeFailure(11); }
        }
        var point = new MetadataRecoveryPoint(id, epoch, Provider, version,
            version == V1 ? "fixture-sqlite-app-v1" : "fixture-sqlite-app-v2", logical);
        var capture = new Capture(point, change, HashFile(destination, budget));
        File.WriteAllText(Path.ChangeExtension(destination, ".json"), JsonSerializer.Serialize(capture, Json));
        return Ok(point);
    }

    private static SqliteConnection OpenFile(string file, bool readOnly)
    {
        var database = new SqliteConnection(new SqliteConnectionStringBuilder
        { DataSource = file, Mode = readOnly ? SqliteOpenMode.ReadOnly : SqliteOpenMode.ReadWrite, Pooling = false, DefaultTimeout = 1 }.ConnectionString);
        try { database.Open(); return database; }
        catch { database.Dispose(); throw; }
    }

    private static long ChangeNumber(SqliteConnection database)
    {
        using var select = new SqliteStatement(database, "SELECT change_number FROM metadata_schema WHERE singleton=1");
        if (!select.Step()) { throw new SqliteNativeFailure(11); }
        return select.Number(0);
    }

    private static string HashFile(string file, SqliteWorkBudget budget)
    {
        using var stream = File.OpenRead(file);
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var buffer = new byte[65536];
        int read;
        while ((read = stream.Read(buffer)) != 0) { budget.Check(); hash.AppendData(buffer.AsSpan(0, read)); }
        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private static string LogicalDigest(SqliteConnection database, SqliteWorkBudget budget)
    {
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        void Add(byte[] value)
        {
            hash.AppendData(BitConverter.GetBytes(System.Net.IPAddress.HostToNetworkOrder(value.Length)));
            hash.AppendData(value);
        }
        foreach (var query in new[]
        {
            "SELECT hex(key),length(CAST(payload AS BLOB)),payload FROM metadata_records ORDER BY key",
            "SELECT hex(entry),length(hex(digest)),hex(digest) FROM metadata_edges ORDER BY entry",
            "SELECT hex(id),length(CAST(json_array(hex(epoch),issued,expires,state,hex(fingerprint),receipt) AS BLOB)),"
                + "json_array(hex(epoch),issued,expires,state,hex(fingerprint),receipt) FROM metadata_operations ORDER BY id"
        })
        {
            Add(Encoding.UTF8.GetBytes(query));
            using var select = new SqliteStatement(database, query);
            while (select.Step())
            {
                budget.Check();
                if (select.Number(1) > MetadataEncoding.MaximumBytes) { throw new SqliteNativeFailure(11); }
                var key = select.Text(0);
                var payload = select.Text(2);
                Add(Encoding.UTF8.GetBytes(key));
                Add(Encoding.UTF8.GetBytes(payload));
            }
        }
        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private Capture VerifyCapture(MetadataRecoveryPoint point, SqliteWorkBudget budget)
    {
        if (point is null || point.Id is null || point.ProviderId != Provider || point.SchemaVersion is not V1 and not V2
            || point.ApplicationVersion != (point.SchemaVersion == V1 ? "fixture-sqlite-app-v1" : "fixture-sqlite-app-v2"))
        { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
        var backup = CapturePath(point.Id);
        var manifest = Path.ChangeExtension(backup, ".json");
        if (!File.Exists(backup) || !File.Exists(manifest) || new FileInfo(manifest).Length > 16384)
        { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
        var capture = JsonSerializer.Deserialize<Capture>(File.ReadAllText(manifest), Json);
        if (capture is null || capture.Point != point || HashFile(backup, budget) != capture.FileDigest)
        { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
        using var verify = OpenFile(backup, readOnly: true);
        VerifyLayout(verify, point.SchemaVersion, budget);
        VerifyLogicalIntegrity(verify, budget);
        if (LogicalDigest(verify, budget) != point.LogicalDigest)
        { throw new SqliteContractFailure(MetadataFailureCode.CorruptState); }
        return capture;
    }
}
