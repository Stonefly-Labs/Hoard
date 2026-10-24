using System.Text;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed record SqliteOperationTestImage(double State, string? FingerprintHex, string? FingerprintText, string? Receipt);

public sealed partial class SqliteMetadataStore
{
    public ValueTask<MetadataResult<string>> RecordPayloadForTestAsync(MetadataSelector selector) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            using var select = new SqliteStatement(Database,
                "SELECT payload FROM metadata_records WHERE key=?1", RecordKey(selector));
            if (!select.Step() || !select.IsText(0)) { throw new ArgumentException("FaultControl.MissingRecord"); }
            if (select.ByteLength(0) > MetadataEncoding.MaximumBytes * 2) { throw new OverflowException(); }
            return ValueTask.FromResult(Ok(select.Text(0)));
        });

    public ValueTask<MetadataResult<MetadataId>> ReplaceRecordPayloadForTestAsync(MetadataSelector selector, string payload) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            RequireRawText(payload);
            return ReplaceRawAsync(budget,
                "UPDATE metadata_records SET payload=?1 WHERE key=?2", payload, RecordKey(selector));
        });

    public ValueTask<MetadataResult<SqliteOperationTestImage>> OperationImageForTestAsync(MetadataOperationTicket ticket) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            MetadataEncoding.ValidateTicket(ticket);
            budget.Check();
            using var select = new SqliteStatement(Database,
                "SELECT state,fingerprint,receipt FROM metadata_operations WHERE id=?1 AND epoch=?2 AND issued=?3 AND expires=?4",
                IdBytes(ticket.Id), IdBytes(ticket.Epoch), ticket.Issued.UnixMilliseconds, ticket.Expires.UnixMilliseconds);
            if (!select.Step()) { throw new ArgumentException("FaultControl.MissingOperation"); }
            if (select.ByteLength(1) > 128 || select.ByteLength(2) > MetadataEncoding.MaximumBytes * 2)
            { throw new OverflowException(); }
            if ((!select.IsBlob(1) && !select.IsText(1) && !select.IsNull(1))
                || (!select.IsText(2) && !select.IsNull(2)))
            { throw new ArgumentException("FaultControl.InvalidStorageClass"); }
            return ValueTask.FromResult(Ok(new SqliteOperationTestImage(select.Real(0),
                select.IsBlob(1) ? Convert.ToHexStringLower(select.Bytes(1)) : null,
                select.IsText(1) ? select.Text(1) : null, select.IsNull(2) ? null : select.Text(2))));
        });

    public ValueTask<MetadataResult<MetadataId>> ReplaceOperationImageForTestAsync(
        MetadataOperationTicket ticket, SqliteOperationTestImage image) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            ArgumentNullException.ThrowIfNull(image);
            MetadataEncoding.ValidateTicket(ticket);
            if (!double.IsFinite(image.State) || image.FingerprintHex is { Length: > 256 }
                || image.FingerprintText is { Length: > 128 }
                || image.FingerprintText is { } text && Encoding.UTF8.GetByteCount(text) > 128
                || image.FingerprintHex is not null && image.FingerprintText is not null)
            { throw new ArgumentException("FaultControl.InvalidImage"); }
            if (image.Receipt is not null) { RequireRawText(image.Receipt); }
            object? fingerprint = image.FingerprintText;
            if (image.FingerprintHex is not null)
            {
                try { fingerprint = Convert.FromHexString(image.FingerprintHex); }
                catch (FormatException) { throw new ArgumentException("FaultControl.InvalidImage"); }
            }
            return ReplaceRawAsync(budget,
                "UPDATE metadata_operations SET state=?1,fingerprint=?2,receipt=?3 "
                + "WHERE id=?4 AND epoch=?5 AND issued=?6 AND expires=?7",
                image.State, fingerprint, image.Receipt, IdBytes(ticket.Id), IdBytes(ticket.Epoch),
                ticket.Issued.UnixMilliseconds, ticket.Expires.UnixMilliseconds);
        });

    private async ValueTask<MetadataResult<MetadataId>> ReplaceRawAsync(
        SqliteWorkBudget budget, string sql, params object?[] arguments)
    {
        await BeginAsync(budget);
        try
        {
            SqliteStatement.Execute(Database, sql, arguments);
            if (SQLitePCL.raw.sqlite3_changes(Database.Handle) != 1)
            { throw new ArgumentException("FaultControl.MissingTarget"); }
            budget.Check();
            SqliteStatement.Execute(Database, "COMMIT");
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0)
            { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
        await observe("sqlite.persisted.changed");
        return Ok(epoch ?? throw new InvalidOperationException("FaultControl.MissingEpoch"));
    }

    private static void RequireRawText(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value.Length > MetadataEncoding.MaximumBytes * 2
            || Encoding.UTF8.GetByteCount(value) > MetadataEncoding.MaximumBytes * 2)
        { throw new ArgumentException("FaultControl.PayloadLimit"); }
    }
}
