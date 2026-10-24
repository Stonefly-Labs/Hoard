using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using static Hoard.Testing.Conformance.Metadata.MetadataCaseData;

namespace Hoard.Testing.Conformance.Metadata;

public static class MetadataPagingAssertions
{
    public static async Task BoundedDatasetsAsync(IMetadataStore store, CancellationToken cancellationToken)
    {
        Assert.Empty(await Traverse(store, Registries(), cancellationToken));
        foreach (var target in new[] { 1, 100, 205 })
        {
            var before = (await Traverse(store, Registries(), cancellationToken)).Length;
            for (var start = before; start < target; start += 64)
            {
                await Commit(store, cancellationToken, Enumerable.Range(start + 1, Math.Min(64, target - start))
                    .Select(number => (MetadataMutation)new MetadataMutation.PutRegistry(Registry(number), new ExpectedRevision.Absent())).ToArray());
            }
            var actual = await Traverse(store, Registries(), cancellationToken);
            Assert.Equal(target, actual.Length);
            Assert.Equal(target, actual.Select(record => record.Selector).Distinct().Count());
            var keys = actual.Select(record => Convert.ToHexStringLower(MetadataEncoding.Key(record.Selector).AsSpan())).ToArray();
            Assert.Equal(keys.Order(StringComparer.Ordinal), keys);
        }
        Assert.Equal(MetadataFailureCode.InvalidInput, Failed(await store.ReadPageAsync(Registries(101), new(), cancellationToken)));
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup(new MetadataSelector[65].ToImmutableArray()));
    }
}
