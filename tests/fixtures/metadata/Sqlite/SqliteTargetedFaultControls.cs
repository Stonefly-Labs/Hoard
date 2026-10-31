using System.Text;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed record SqliteOperationTestImage(double State, string? FingerprintHex, string? FingerprintText, string? Receipt);

public sealed partial class SqliteMetadataStore
{
    public ValueTask<MetadataResult<string>> RecordPayloadForTestAsync(MetadataSelector selector) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            return ValueTask.FromResult(Ok(ReadRecordPayload(Database, selector)));
        });

    public ValueTask<MetadataResult<string>> ObserveRecordPayloadForTestAsync(
        MetadataSelector selector, CancellationToken cancellationToken) =>
        worker.SubmitIndependent(cancellationToken, budget =>
        {
            budget.Check();
            using var independent = OpenFile(path, readOnly: true);
            var payload = ReadRecordPayload(independent, selector);
            budget.Check();
            return ValueTask.FromResult(Ok(payload));
        });

    private static string ReadRecordPayload(SqliteConnection database, MetadataSelector selector)
    {
        using var select = new SqliteStatement(database,
            "SELECT payload FROM metadata_records WHERE key=?1", RecordKey(selector));
        if (!select.Step() || !select.IsText(0)) { throw new ArgumentException("FaultControl.MissingRecord"); }
        if (select.ByteLength(0) > MetadataEncoding.MaximumBytes * 2) { throw new OverflowException(); }
        return select.Text(0);
    }

    public ValueTask<MetadataResult<MetadataId>> ReplaceRecordPayloadForTestAsync(MetadataSelector selector, string payload) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            RequireRawText(payload);
            return ReplaceRawAsync(budget,
                "UPDATE metadata_records SET payload=?1 WHERE key=?2", payload, RecordKey(selector));
        });

    public ValueTask<MetadataResult<MetadataId>> CompareExchangeRecordPayloadForTestAsync(
        MetadataSelector selector, string expected, string payload, Action? applied = null) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            RequireRawText(payload);
            return ReplaceRawAsync(budget, "UPDATE metadata_records SET payload=?1 WHERE key=?2",
                () => ReadRecordPayload(Database, selector) == expected, applied, payload, RecordKey(selector));
        });

    public ValueTask<MetadataResult<SqliteOperationTestImage>> OperationImageForTestAsync(MetadataOperationTicket ticket) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            return ValueTask.FromResult(Ok(ReadOperationImage(Database, ticket)));
        });

    public ValueTask<MetadataResult<SqliteOperationTestImage>> ObserveOperationImageForTestAsync(
        MetadataOperationTicket ticket, CancellationToken cancellationToken) =>
        worker.SubmitIndependent(cancellationToken, budget =>
        {
            budget.Check();
            using var independent = OpenFile(path, readOnly: true);
            var image = ReadOperationImage(independent, ticket);
            budget.Check();
            return ValueTask.FromResult(Ok(image));
        });

    private static SqliteOperationTestImage ReadOperationImage(SqliteConnection database, MetadataOperationTicket ticket)
    {
        MetadataEncoding.ValidateTicket(ticket);
        using var select = new SqliteStatement(database,
            "SELECT state,fingerprint,receipt FROM metadata_operations WHERE id=?1 AND epoch=?2 AND issued=?3 AND expires=?4",
            IdBytes(ticket.Id), IdBytes(ticket.Epoch), ticket.Issued.UnixMilliseconds, ticket.Expires.UnixMilliseconds);
        if (!select.Step()) { throw new ArgumentException("FaultControl.MissingOperation"); }
        if (select.ByteLength(1) > 128 || select.ByteLength(2) > MetadataEncoding.MaximumBytes * 2)
        { throw new OverflowException(); }
        if ((!select.IsBlob(1) && !select.IsText(1) && !select.IsNull(1))
            || (!select.IsText(2) && !select.IsNull(2)))
        { throw new ArgumentException("FaultControl.InvalidStorageClass"); }
        return new(select.Real(0),
            select.IsBlob(1) ? Convert.ToHexStringLower(select.Bytes(1)) : null,
            select.IsText(1) ? select.Text(1) : null, select.IsNull(2) ? null : select.Text(2));
    }

    public ValueTask<MetadataResult<MetadataId>> ReplaceOperationImageForTestAsync(
        MetadataOperationTicket ticket, SqliteOperationTestImage image) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            return ReplaceRawAsync(budget, OperationImageUpdate, OperationImageArguments(ticket, image));
        });

    public ValueTask<MetadataResult<MetadataId>> CompareExchangeOperationImageForTestAsync(
        MetadataOperationTicket ticket, SqliteOperationTestImage expected, SqliteOperationTestImage image, Action? applied = null) =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
            ReplaceRawAsync(budget, OperationImageUpdate,
                () => ReadOperationImage(Database, ticket) == expected, applied, OperationImageArguments(ticket, image)));

    private const string OperationImageUpdate = "UPDATE metadata_operations SET state=?1,fingerprint=?2,receipt=?3 "
        + "WHERE id=?4 AND epoch=?5 AND issued=?6 AND expires=?7";

    private static object?[] OperationImageArguments(MetadataOperationTicket ticket, SqliteOperationTestImage image)
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
        return [image.State, fingerprint, image.Receipt, IdBytes(ticket.Id), IdBytes(ticket.Epoch),
            ticket.Issued.UnixMilliseconds, ticket.Expires.UnixMilliseconds];
    }

    private ValueTask<MetadataResult<MetadataId>> ReplaceRawAsync(
        SqliteWorkBudget budget, string sql, params object?[] arguments) =>
        ReplaceRawAsync(budget, sql, null, null, arguments);

    private async ValueTask<MetadataResult<MetadataId>> ReplaceRawAsync(
        SqliteWorkBudget budget, string sql, Func<bool>? matches, Action? applied, params object?[] arguments)
    {
        await BeginAsync(budget);
        try
        {
            if (matches is not null && !matches()) { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
            SqliteStatement.Execute(Database, sql, arguments);
            if (SQLitePCL.raw.sqlite3_changes(Database.Handle) != 1)
            { throw new ArgumentException("FaultControl.MissingTarget"); }
            budget.Check();
            SqliteStatement.Execute(Database, "COMMIT");
            applied?.Invoke();
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
