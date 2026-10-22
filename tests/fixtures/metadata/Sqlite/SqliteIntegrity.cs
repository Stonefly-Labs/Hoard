using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private static string Shape(string sql) => new(sql.Where(character => !char.IsWhiteSpace(character) && character != '"').ToArray());

    private static void VerifyLayout(SqliteConnection database, string schemaVersion, SqliteWorkBudget budget)
    {
        using var resource = typeof(SqliteMetadataStore).Assembly.GetManifestResourceStream(
            "Hoard.Fixtures.Metadata.Sqlite." + (schemaVersion == V1 ? "SchemaV1.sql" : "SchemaV2.sql"))
            ?? throw new InvalidOperationException("Missing private schema inventory.");
        using var reader = new StreamReader(resource);
        var expected = reader.ReadToEnd().Split(';', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
            .Select(Shape).ToHashSet(StringComparer.Ordinal);
        using var objects = new SqliteStatement(database, "SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL");
        while (objects.Step())
        {
            budget.Check();
            if (!expected.Remove(Shape(objects.Text(0)))) { throw new SqliteContractFailure(MetadataFailureCode.IncompatibleSchema); }
        }
        if (expected.Count != 0) { throw new SqliteContractFailure(MetadataFailureCode.IncompatibleSchema); }
    }

    private static MetadataRecord ReadStoredRecord(SqliteStatement select, int lengthColumn, int payloadColumn)
    {
        if (select.IsNull(lengthColumn) || select.Number(lengthColumn) is < 1 or > MetadataEncoding.MaximumBytes)
        { throw new SqliteNativeFailure(11); }
        try
        {
            var record = JsonSerializer.Deserialize<MetadataRecord>(select.Text(payloadColumn), Json) ?? throw new SqliteNativeFailure(11);
            _ = MetadataEncoding.Encode(record);
            return record;
        }
        catch (ArgumentException) { throw new SqliteNativeFailure(11); }
        catch (JsonException) { throw new SqliteNativeFailure(11); }
    }

    private void VerifyLogicalIntegrity(SqliteConnection database, SqliteWorkBudget budget)
    {
        MetadataRecord? Read(MetadataSelector selector) => Get(selector, database);
        using (var records = new SqliteStatement(database,
            "SELECT key,kind,registry,package,policy,ecosystem,length(CAST(payload AS BLOB)),payload FROM metadata_records ORDER BY key"))
        {
            while (records.Step())
            {
                budget.Check();
                var record = ReadStoredRecord(records, 6, 7);
                var key = RecordKey(record.Selector);
                if (!records.Bytes(0).AsSpan().SequenceEqual(key) || records.Number(1) != key[0]) { throw new SqliteNativeFailure(11); }
                var index = IndexValues(record);
                var columns = new[] { index.Registry, index.Package, index.Policy, index.Ecosystem };
                for (var column = 0; column < columns.Length; column++)
                {
                    if (columns[column] is { } value ? records.IsNull(column + 2)
                        || !records.Bytes(column + 2).AsSpan().SequenceEqual(value) : !records.IsNull(column + 2))
                    { throw new SqliteNativeFailure(11); }
                }
                switch (record)
                {
                    case MetadataRegistry registry:
                        if (registry.PolicyId is MetadataOption<MetadataId>.Some policy
                            && (Read(new MetadataSelector.Policy(policy.Value)) is not MetadataPolicy linked
                                || linked.Scope is MetadataPolicyScope.Registry linkedScope && linkedScope.Id != registry.Id))
                        { throw new SqliteNativeFailure(11); }
                        break;
                    case MetadataPackage package:
                        if (Read(new MetadataSelector.Registry(package.Key.RegistryId)) is not MetadataRegistry parent
                            || parent.Ecosystem != package.Key.Ecosystem) { throw new SqliteNativeFailure(11); }
                        break;
                    case MetadataPolicy { Scope: MetadataPolicyScope.Registry scope }:
                        if (Read(new MetadataSelector.Registry(scope.Id)) is null) { throw new SqliteNativeFailure(11); }
                        break;
                    case MetadataAccessAggregate aggregate:
                        if (Read(new MetadataSelector.Registry(aggregate.Key.RegistryId)) is null) { throw new SqliteNativeFailure(11); }
                        break;
                    case MetadataCacheEntry entry:
                        if (Read(new MetadataSelector.Registry(entry.Identity.RegistryId)) is not MetadataRegistry entryRegistry
                            || entryRegistry.Ecosystem != entry.Identity.Ecosystem || Read(new MetadataSelector.Package(entry.Package)) is null
                            || Read(new MetadataSelector.Artifact(entry.Digest)) is not MetadataArtifactState entryArtifact || entryArtifact.Length != entry.Length)
                        { throw new SqliteNativeFailure(11); }
                        using (var edge = new SqliteStatement(database, "SELECT digest FROM metadata_edges WHERE entry=?1", key))
                        {
                            if (!edge.Step() || !edge.Bytes(0).AsSpan().SequenceEqual(RecordKey(new MetadataSelector.Artifact(entry.Digest))) || edge.Step())
                            { throw new SqliteNativeFailure(11); }
                        }
                        break;
                    case MetadataArtifactState artifact:
                        using (var count = new SqliteStatement(database, "SELECT count(*) FROM metadata_edges WHERE digest=?1", key))
                        { if (!count.Step() || count.Number(0) != artifact.LiveReferences) { throw new SqliteNativeFailure(11); } }
                        break;
                }
            }
        }
        using (var edges = new SqliteStatement(database,
            "SELECT 1 FROM metadata_edges e JOIN metadata_records a ON a.key=e.entry JOIN metadata_records b ON b.key=e.digest WHERE a.kind<>4 OR b.kind<>5 LIMIT 1"))
        { if (edges.Step()) { throw new SqliteNativeFailure(11); } }
        using var operations = new SqliteStatement(database,
            "SELECT id,epoch,issued,expires,state,length(fingerprint),length(CAST(receipt AS BLOB)),receipt,fingerprint "
            + "FROM metadata_operations ORDER BY id");
        var countOperations = 0;
        while (operations.Step())
        {
            budget.Check();
            if (++countOperations > 100000)
            { throw new SqliteNativeFailure(11); }
            _ = ReadStoredOperation(operations);
        }
    }

    private sealed record RecordIndexes(byte[]? Registry, byte[]? Package, byte[]? Policy, byte[]? Ecosystem);
    private static RecordIndexes IndexValues(MetadataRecord record) => new(record switch
    {
        MetadataPackage package => IdBytes(package.Key.RegistryId),
        MetadataCacheEntry entry => IdBytes(entry.Identity.RegistryId),
        MetadataAccessAggregate aggregate => IdBytes(aggregate.Key.RegistryId),
        MetadataPolicy { Scope: MetadataPolicyScope.Registry scope } => IdBytes(scope.Id),
        _ => null
    },
    record is MetadataCacheEntry cache ? RecordKey(new MetadataSelector.Package(cache.Package)) : null,
    record is MetadataRegistry { PolicyId: MetadataOption<MetadataId>.Some policy } ? RecordKey(new MetadataSelector.Policy(policy.Value)) : null,
    record switch
    {
        MetadataRegistry value => Encoding.UTF8.GetBytes(value.Ecosystem.Value),
        MetadataPackage value => Encoding.UTF8.GetBytes(value.Key.Ecosystem.Value),
        MetadataCacheEntry value => Encoding.UTF8.GetBytes(value.Identity.Ecosystem.Value),
        _ => null
    });
}
