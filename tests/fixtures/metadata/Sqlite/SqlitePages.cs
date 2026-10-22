using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private sealed record Cursor(int ContractVersion, MetadataId Epoch, string Schema, string Query, int PageSize, string LastKey);

    private ValueTask<MetadataResult<MetadataPage>> ReadPageCoreAsync(MetadataPageQuery query, SqliteWorkBudget budget)
    {
        _ = MetadataEncoding.Encode(query);
        var binding = Convert.ToHexStringLower(SHA256.HashData(MetadataEncoding.Encode(
            query with { Continuation = new MetadataOption<MetadataContinuation>.None() }).AsSpan()));
        byte[] after = [];
        if (query.Continuation is MetadataOption<MetadataContinuation>.Some continuation)
        {
            Cursor cursor;
            try
            {
                var bytes = Convert.FromBase64String(continuation.Value.Value);
                if (bytes.Length > 12288) { throw new ArgumentException("Oversized metadata continuation."); }
                cursor = JsonSerializer.Deserialize<Cursor>(bytes, Json) ?? throw new ArgumentException("Invalid metadata continuation.");
                if (cursor.ContractVersion != 1 || cursor.Epoch != epoch || cursor.Schema != version
                    || cursor.Query != binding || cursor.PageSize != query.PageSize
                    || cursor.LastKey is not { Length: >= 2 and <= 16384 })
                { throw new ArgumentException("Foreign or changed metadata continuation."); }
                after = Convert.FromHexString(cursor.LastKey);
            }
            catch (FormatException) { throw new ArgumentException("Invalid metadata continuation."); }
            catch (JsonException) { throw new ArgumentException("Invalid metadata continuation."); }
        }
        var kind = query switch
        {
            MetadataPageQuery.Registries => 1,
            MetadataPageQuery.Packages => 2,
            MetadataPageQuery.Policies => 3,
            MetadataPageQuery.CacheEntries => 4,
            MetadataPageQuery.Artifacts => 5,
            MetadataPageQuery.Leases => 6,
            MetadataPageQuery.Aggregates => 7,
            _ => throw new ArgumentException("Invalid page query.")
        };
        var filters = new List<string> { "kind=?1", "key>?2" };
        var arguments = new List<object?> { kind, after };
        void Filter(string column, object value)
        {
            arguments.Add(value);
            filters.Add(column + "=?" + arguments.Count);
        }
        switch (query)
        {
            case MetadataPageQuery.Packages packages: Filter("registry", IdBytes(packages.RegistryId)); break;
            case MetadataPageQuery.CacheEntries entries:
                Filter("registry", IdBytes(entries.RegistryId));
                Filter("json_extract(payload,'$.Identity.AuthorizationPartition.Value')", entries.AuthorizationPartition.Value);
                if (entries.Package is MetadataOption<MetadataPackageKey>.Some package)
                { Filter("package", RecordKey(new MetadataSelector.Package(package.Value))); }
                break;
            case MetadataPageQuery.Policies { Scope: MetadataPolicyScope.Global }: filters.Add("registry IS NULL"); break;
            case MetadataPageQuery.Policies { Scope: MetadataPolicyScope.Registry registry }: Filter("registry", IdBytes(registry.Id)); break;
            case MetadataPageQuery.Aggregates aggregates:
                Filter("registry", IdBytes(aggregates.RegistryId));
                Filter("json_extract(payload,'$.Key.AuthorizationPartition.Value')", aggregates.AuthorizationPartition.Value);
                Filter("json_extract(payload,'$.Key.Start.UnixMilliseconds')", aggregates.Start.UnixMilliseconds);
                Filter("json_extract(payload,'$.Key.End.UnixMilliseconds')", aggregates.End.UnixMilliseconds);
                break;
            case MetadataPageQuery.Leases leases:
                arguments.Add(Encoding.UTF8.GetBytes(leases.ResourcePrefix.Value));
                filters.Add("substr(CAST(json_extract(payload,'$.Resource.Value') AS BLOB),1,length(?" + arguments.Count + "))=?" + arguments.Count);
                break;
        }
        arguments.Add(query.PageSize + 1);
        SqliteStatement.Execute(Database, "BEGIN");
        try
        {
            using var select = new SqliteStatement(Database,
                "SELECT key,length(CAST(payload AS BLOB)),payload FROM metadata_records WHERE "
                + string.Join(" AND ", filters) + " ORDER BY key LIMIT ?" + arguments.Count, arguments.ToArray());
            var records = ImmutableArray.CreateBuilder<MetadataRecord>(query.PageSize);
            byte[]? last = null;
            var more = false;
            while (select.Step())
            {
                budget.Check();
                if (records.Count == query.PageSize) { more = true; break; }
                if (select.Number(1) > MetadataEncoding.MaximumBytes) { throw new SqliteNativeFailure(11); }
                last = select.Bytes(0);
                records.Add(DecodeRecord(select.Text(2), last));
            }
            MetadataOption<MetadataContinuation> next = more && last is not null
                ? new MetadataOption<MetadataContinuation>.Some(new(Convert.ToBase64String(
                    JsonSerializer.SerializeToUtf8Bytes(new Cursor(1, epoch!, version, binding, query.PageSize, Convert.ToHexStringLower(last)), Json))))
                : new MetadataOption<MetadataContinuation>.None();
            var page = new MetadataPage(records.ToImmutable(), next);
            _ = MetadataEncoding.Encode(page);
            budget.Check();
            SqliteStatement.Execute(Database, "COMMIT");
            return ValueTask.FromResult(Ok(page));
        }
        finally
        {
            if (SQLitePCL.raw.sqlite3_get_autocommit(Database.Handle) == 0) { SqliteStatement.Execute(Database, "ROLLBACK"); }
        }
    }
}
