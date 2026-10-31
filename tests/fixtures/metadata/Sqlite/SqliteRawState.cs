using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    public ValueTask<MetadataResult<string>> RawStateFingerprintForTestAsync(CancellationToken cancellationToken) =>
        worker.Submit(TimeSpan.FromSeconds(5), cancellationToken, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            OwnStore();
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            long bytes = 0;
            void Add(IncrementalHash target, ReadOnlySpan<byte> value)
            {
                budget.Check();
                bytes = checked(bytes + value.Length + sizeof(long));
                if (bytes > 256 * 1024 * 1024) { throw new OverflowException(); }
                Span<byte> size = stackalloc byte[sizeof(long)];
                BinaryPrimitives.WriteInt64BigEndian(size, value.Length);
                target.AppendData(size);
                target.AppendData(value);
            }
            if (!File.Exists(path)) { Add(hash, "missing"u8); }
            else
            {
                using var database = Open(readOnly: true);
                var nativeLimit = MetadataEncoding.MaximumBytes * 2 + 65536;
                SQLitePCL.raw.sqlite3_limit(database.Handle, SQLitePCL.raw.SQLITE_LIMIT_LENGTH,
                    Math.Min(nativeLimit, SQLitePCL.raw.sqlite3_limit(database.Handle, SQLitePCL.raw.SQLITE_LIMIT_LENGTH, -1)));
                SQLitePCL.raw.sqlite3_progress_handler(database.Handle, 1000,
                    _ => budget.Cancelled || budget.Expired || budget.Abandoned ? 1 : 0, null);
                SqliteStatement.Execute(database, "BEGIN");
                try
                {
                    var tables = new List<string>();
                    var objects = new List<string[]>();
                    using (var schema = new SqliteStatement(database,
                        "SELECT type,name,tbl_name,coalesce(sql,'') FROM sqlite_schema LIMIT 129"))
                    {
                        while (schema.Step())
                        {
                            if (objects.Count >= 128) { throw new OverflowException(); }
                            var fields = new string[4];
                            for (var index = 0; index < 4; index++)
                            {
                                if (schema.ByteLength(index) > 65536) { throw new OverflowException(); }
                                fields[index] = schema.Text(index);
                            }
                            objects.Add(fields);
                        }
                    }
                    objects.Sort(static (left, right) =>
                    {
                        var type = StringComparer.Ordinal.Compare(left[0], right[0]);
                        return type == 0 ? StringComparer.Ordinal.Compare(left[1], right[1]) : type;
                    });
                    foreach (var fields in objects)
                    {
                        foreach (var field in fields) { Add(hash, Encoding.UTF8.GetBytes(field)); }
                        if (fields[0] == "table") { tables.Add(fields[1]); }
                    }
                    long rows = 0;
                    foreach (var table in tables)
                    {
                        budget.Check();
                        var columns = new List<string>();
                        using (var info = new SqliteStatement(database, "SELECT name FROM pragma_table_xinfo(?1) ORDER BY cid", table))
                        {
                            while (info.Step())
                            {
                                if (columns.Count >= 64 || info.ByteLength(0) > 1024) { throw new OverflowException(); }
                                columns.Add(QuoteIdentifier(info.Text(0)));
                            }
                        }
                        if (columns.Count == 0) { throw new InvalidOperationException("FaultControl.InvalidLayout"); }
                        var sizes = string.Join("+", columns.Select(column => $"coalesce(length(CAST({column} AS BLOB)),0)"));
                        using (var preflight = new SqliteStatement(database,
                            $"SELECT {sizes} FROM {QuoteIdentifier(table)} LIMIT {1_000_001 - rows}"))
                        {
                            var checkedRows = rows;
                            var checkedBytes = bytes;
                            while (preflight.Step())
                            {
                                budget.Check();
                                var size = preflight.Number(0);
                                checkedBytes = checked(checkedBytes + size);
                                if (++checkedRows > 1_000_000 || size > nativeLimit || checkedBytes > 256 * 1024 * 1024)
                                { throw new OverflowException(); }
                            }
                        }
                        Add(hash, Encoding.UTF8.GetBytes(table));
                        var selected = columns.Select(column => $"length(CAST({column} AS BLOB)),{column}");
                        using var contents = new SqliteStatement(database,
                            $"SELECT {string.Join(",", selected)} FROM {QuoteIdentifier(table)}");
                        using var rowHash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                        var digests = new List<byte[]>();
                        while (contents.Step())
                        {
                            if (++rows > 1_000_000) { throw new OverflowException(); }
                            for (var index = 0; index < columns.Count; index++)
                            {
                                budget.Check();
                                var value = index * 2 + 1;
                                if (contents.Number(index * 2) > MetadataEncoding.MaximumBytes * 2)
                                { throw new OverflowException(); }
                                if (contents.IsNull(value)) { Add(rowHash, "null"u8); }
                                else if (contents.IsInteger(value))
                                { Add(rowHash, "integer"u8); Add(rowHash, NumberBytes(contents.Number(value))); }
                                else if (contents.IsBlob(value))
                                { Add(rowHash, "blob"u8); Add(rowHash, contents.Bytes(value)); }
                                else if (contents.IsText(value))
                                { Add(rowHash, "text"u8); Add(rowHash, contents.Bytes(value)); }
                                else
                                { Add(rowHash, "real"u8); Add(rowHash, NumberBytes(BitConverter.DoubleToInt64Bits(contents.Real(value)))); }
                            }
                            digests.Add(rowHash.GetHashAndReset());
                        }
                        digests.Sort(static (left, right) => left.AsSpan().SequenceCompareTo(right));
                        foreach (var digest in digests) { Add(hash, digest); }
                    }
                    SqliteStatement.Execute(database, "COMMIT");
                }
                catch (SqliteNativeFailure error) when (error.Code == 9) { budget.Check(); throw; }
                catch (SqliteNativeFailure error) when (error.Code == 18) { throw new OverflowException(); }
                finally
                {
                    SQLitePCL.raw.sqlite3_progress_handler(database.Handle, 0, null, null);
                    if (SQLitePCL.raw.sqlite3_get_autocommit(database.Handle) == 0)
                    { SqliteStatement.Execute(database, "ROLLBACK"); }
                }
            }
            return ValueTask.FromResult(Ok(Convert.ToHexStringLower(hash.GetHashAndReset())));
        });

    private static string QuoteIdentifier(string name) => "\"" + name.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"";

    private static byte[] NumberBytes(long value)
    {
        var bytes = new byte[sizeof(long)];
        BinaryPrimitives.WriteInt64BigEndian(bytes, value);
        return bytes;
    }
}
