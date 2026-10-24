using Microsoft.Data.Sqlite;
using SQLitePCL;

namespace Hoard.Fixtures.Metadata.Sqlite;

internal sealed class SqliteNativeFailure(int code) : Exception("Private SQLite operation failed.")
{
    public int Code { get; } = code & 255;
}

internal sealed class SqliteStatement : IDisposable
{
    private readonly sqlite3_stmt statement;

    public SqliteStatement(SqliteConnection connection, string sql, params object?[] parameters)
    {
        var code = raw.sqlite3_prepare_v2(connection.Handle, sql, out statement);
        if (code != raw.SQLITE_OK) { statement?.Dispose(); throw new SqliteNativeFailure(code); }
        try
        {
            for (var index = 0; index < parameters.Length; index++)
            {
                code = parameters[index] switch
                {
                    null => raw.sqlite3_bind_null(statement, index + 1),
                    byte[] bytes => raw.sqlite3_bind_blob(statement, index + 1, bytes),
                    string text => raw.sqlite3_bind_text(statement, index + 1, text),
                    int number => raw.sqlite3_bind_int(statement, index + 1, number),
                    long number => raw.sqlite3_bind_int64(statement, index + 1, number),
                    double number when double.IsFinite(number) => raw.sqlite3_bind_double(statement, index + 1, number),
                    _ => throw new ArgumentException("Unsupported private SQL parameter.")
                };
                if (code != raw.SQLITE_OK) { throw new SqliteNativeFailure(code); }
            }
        }
        catch { statement.Dispose(); throw; }
    }

    public bool Step()
    {
        var code = raw.sqlite3_step(statement);
        return code switch
        {
            raw.SQLITE_ROW => true,
            raw.SQLITE_DONE => false,
            _ => throw new SqliteNativeFailure(code)
        };
    }
    public long Number(int index) => raw.sqlite3_column_int64(statement, index);
    public double Real(int index) => raw.sqlite3_column_double(statement, index);
    public int ByteLength(int index) => raw.sqlite3_column_bytes(statement, index);
    public string Text(int index) => raw.sqlite3_column_text(statement, index).utf8_to_string();
    public byte[] Bytes(int index) => raw.sqlite3_column_blob(statement, index).ToArray();
    public bool IsNull(int index) => raw.sqlite3_column_type(statement, index) == raw.SQLITE_NULL;
    public bool IsInteger(int index) => raw.sqlite3_column_type(statement, index) == raw.SQLITE_INTEGER;
    public bool IsBlob(int index) => raw.sqlite3_column_type(statement, index) == raw.SQLITE_BLOB;
    public bool IsText(int index) => raw.sqlite3_column_type(statement, index) == raw.SQLITE_TEXT;
    public void Dispose() => statement.Dispose();

    public static void Execute(SqliteConnection connection, string sql, params object?[] parameters)
    {
        using var command = new SqliteStatement(connection, sql, parameters);
        if (command.Step()) { throw new InvalidOperationException("Unexpected private SQL rows."); }
    }
}
