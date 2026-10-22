using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    public ValueTask<MetadataResult<MetadataSchemaAdmission>> RestoreToIsolatedTargetAsync(
        MetadataRecoveryPoint point, string destination, IReadOnlySet<ArtifactDigest> availableArtifacts,
        MetadataAdministrationOptions options, CancellationToken cancellationToken)
    {
        Volatile.Write(ref admitted, 0);
        return Admin(options, cancellationToken, async budget =>
        {
            ArgumentNullException.ThrowIfNull(availableArtifacts);
            if (availableArtifacts.Count > 100000) { throw new ArgumentException("Synthetic artifact set exceeds fixture bound."); }
            var target = Path.GetFullPath(destination);
            if (target == path || File.Exists(target) || !Directory.Exists(Path.GetDirectoryName(target)))
            { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
            var capture = VerifyCapture(point, budget);
            using var source = OpenFile(CapturePath(point.Id), readOnly: true);
            using (var records = new SqliteStatement(source, "SELECT length(CAST(payload AS BLOB)),payload FROM metadata_records WHERE kind=4 ORDER BY key"))
            {
                while (records.Step())
                {
                    budget.Check();
                    var entry = ReadStoredRecord(records, 0, 1) as MetadataCacheEntry ?? throw new SqliteNativeFailure(11);
                    if (!availableArtifacts.Contains(entry.Digest))
                    { throw new SqliteContractFailure(MetadataFailureCode.Unavailable); }
                }
            }
            await observe("restore.before_native");
            budget.Check();
            using var ownershipTarget = new FileStream(target + ".owner", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            var staging = target + ".restore-" + Guid.NewGuid().ToString("N");
            var restoredEpoch = new MetadataId(Guid.NewGuid());
            try
            {
                using (var claim = new FileStream(staging, FileMode.CreateNew, FileAccess.ReadWrite, FileShare.None)) { }
                using (var restored = OpenFile(staging, readOnly: false))
                {
                    source.BackupDatabase(restored);
                    await observe("restore.after_native");
                    budget.Check();
                    using (var mode = new SqliteStatement(restored, "PRAGMA journal_mode=DELETE"))
                    {
                        if (!mode.Step() || mode.Text(0) != "delete" || mode.Step()) { throw new SqliteNativeFailure(1); }
                    }
                    VerifyLayout(restored, capture.Point.SchemaVersion, budget);
                    VerifyLogicalIntegrity(restored, budget);
                    if (LogicalDigest(restored, budget) != capture.Point.LogicalDigest || ChangeNumber(restored) != capture.ChangeNumber)
                    { throw new SqliteNativeFailure(11); }
                    SqliteStatement.Execute(restored, "PRAGMA synchronous=FULL");
                    SqliteStatement.Execute(restored, "BEGIN IMMEDIATE");
                    try
                    {
                        SqliteStatement.Execute(restored, "UPDATE metadata_schema SET epoch=?1 WHERE singleton=1", IdBytes(restoredEpoch));
                        if (!budget.TryCommitDecision()) { throw new SqliteBudgetFailure(budget.Cancelled); }
                        SqliteStatement.Execute(restored, "COMMIT");
                        budget.Committed();
                    }
                    finally
                    {
                        if (SQLitePCL.raw.sqlite3_get_autocommit(restored.Handle) == 0) { SqliteStatement.Execute(restored, "ROLLBACK"); }
                    }
                }
                await observe("restore.before_install");
                budget.Check();
                File.Move(staging, target, overwrite: false);
                return Ok(new MetadataSchemaAdmission(Provider, capture.Point.SchemaVersion, restoredEpoch, true));
            }
            finally { if (File.Exists(staging)) { File.Delete(staging); } }
        });
    }
}
