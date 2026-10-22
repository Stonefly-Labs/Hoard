using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed record SqliteFixtureConfiguration(
    string JournalMode, long Synchronous, long ForeignKeys, long BusyTimeout, string NativeVersion, string Driver);

public sealed partial class SqliteMetadataStore
{
    public ValueTask<MetadataResult<string>> LogicalDigestForTestAsync() =>
        worker.Submit(TimeSpan.FromSeconds(30), default, MetadataPhase.Schema, null, budget =>
        {
            SqliteStatement.Execute(Database, "BEGIN");
            try
            {
                var result = LogicalDigest(Database, budget);
                SqliteStatement.Execute(Database, "COMMIT");
                return ValueTask.FromResult(Ok(result));
            }
            finally
            {
                if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
            }
        });

    public ValueTask<MetadataResult<SqliteFixtureConfiguration>> ConfigurationForTestAsync() =>
        worker.Submit(TimeSpan.FromSeconds(5), default, MetadataPhase.Schema, null, budget =>
        {
            budget.Check();
            string Text(string sql)
            {
                using var value = new SqliteStatement(Database, sql);
                if (!value.Step()) { throw new SqliteNativeFailure(11); }
                return value.Text(0);
            }
            long Number(string sql)
            {
                using var value = new SqliteStatement(Database, sql);
                if (!value.Step()) { throw new SqliteNativeFailure(11); }
                return value.Number(0);
            }
            return ValueTask.FromResult(Ok(new SqliteFixtureConfiguration(Text("PRAGMA journal_mode"),
                Number("PRAGMA synchronous"), Number("PRAGMA foreign_keys"), Number("PRAGMA busy_timeout"),
                Text("SELECT sqlite_version()"), typeof(Microsoft.Data.Sqlite.SqliteConnection).Assembly.GetName().Version!.ToString())));
        });

    public (string Version, string LogicalDigest) ObserveIndependentLayoutForTest()
    {
        using var independent = OpenFile(path, readOnly: true);
        using var version = new SqliteStatement(independent, "SELECT version FROM metadata_schema WHERE singleton=1");
        if (!version.Step()) { throw new SqliteNativeFailure(11); }
        var observed = version.Text(0);
        var budget = new SqliteWorkBudget(TimeSpan.FromSeconds(5), default);
        VerifyLayout(independent, observed, budget);
        VerifyLogicalIntegrity(independent, budget);
        return (observed, LogicalDigest(independent, budget));
    }
}
