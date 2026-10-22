using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text.Json;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore
{
    private sealed record MemoryCursor(int Contract, MetadataId Epoch, string Query, int Size, string After);

    private ValueTask<MetadataResult<MetadataPage>> PageCoreAsync(MetadataPageQuery query, MemoryActivity activity)
    {
        _ = MetadataEncoding.Encode(query);
        var captured = Volatile.Read(ref state);
        var binding = Convert.ToHexStringLower(SHA256.HashData(MetadataEncoding.Encode(
            query with { Continuation = new MetadataOption<MetadataContinuation>.None() }).AsSpan()));
        byte[] after = [];
        if (query.Continuation is MetadataOption<MetadataContinuation>.Some supplied)
        {
            try
            {
                var cursor = JsonSerializer.Deserialize<MemoryCursor>(Convert.FromBase64String(supplied.Value.Value));
                if (cursor is null || cursor.Contract != 1 || cursor.Epoch != captured.Epoch || cursor.Query != binding
                    || cursor.Size != query.PageSize || cursor.After is not { Length: >= 2 and <= 16384 })
                { throw new ArgumentException("Invalid or foreign memory continuation."); }
                after = Convert.FromHexString(cursor.After);
            }
            catch (JsonException) { throw new ArgumentException("Invalid memory continuation."); }
            catch (FormatException) { throw new ArgumentException("Invalid memory continuation."); }
        }
        var candidates = new SortedDictionary<string, MetadataRecord>(StringComparer.Ordinal);
        foreach (var record in captured.Records.Values)
        {
            activity.Check();
            var include = query switch
            {
                MetadataPageQuery.Registries => record is MetadataRegistry,
                MetadataPageQuery.Packages packages => record is MetadataPackage package && package.Key.RegistryId == packages.RegistryId,
                MetadataPageQuery.Policies policies => record is MetadataPolicy policy && policy.Scope == policies.Scope,
                MetadataPageQuery.CacheEntries entries => record is MetadataCacheEntry entry
                    && entry.Identity.RegistryId == entries.RegistryId && entry.Identity.AuthorizationPartition == entries.AuthorizationPartition
                    && (entries.Package is MetadataOption<MetadataPackageKey>.None
                        || entries.Package is MetadataOption<MetadataPackageKey>.Some package && package.Value == entry.Package),
                MetadataPageQuery.Aggregates aggregates => record is MetadataAccessAggregate aggregate
                    && aggregate.Key.RegistryId == aggregates.RegistryId && aggregate.Key.AuthorizationPartition == aggregates.AuthorizationPartition
                    && aggregate.Key.Start == aggregates.Start && aggregate.Key.End == aggregates.End,
                MetadataPageQuery.Leases leases => record is MetadataWorkLease lease
                    && lease.Resource.Value.StartsWith(leases.ResourcePrefix.Value, StringComparison.Ordinal),
                MetadataPageQuery.Artifacts => record is MetadataArtifactState,
                _ => false
            };
            if (!include) { continue; }
            var key = MetadataEncoding.Key(record.Selector);
            if (key.AsSpan().SequenceCompareTo(after) <= 0) { continue; }
            candidates.Add(Convert.ToHexStringLower(key.AsSpan()), record);
            if (candidates.Count > query.PageSize + 1) { candidates.Remove(candidates.Keys.Last()); }
        }
        var selected = candidates.Take(query.PageSize).ToArray();
        MetadataOption<MetadataContinuation> next = candidates.Count > query.PageSize
            ? new MetadataOption<MetadataContinuation>.Some(new(Convert.ToBase64String(JsonSerializer.SerializeToUtf8Bytes(
                new MemoryCursor(1, captured.Epoch, binding, query.PageSize, selected[^1].Key)))))
            : new MetadataOption<MetadataContinuation>.None();
        var page = new MetadataPage(selected.Select(pair => pair.Value).ToImmutableArray(), next);
        _ = MetadataEncoding.Encode(page);
        activity.Check();
        return ValueTask.FromResult(Success(page));
    }
}
