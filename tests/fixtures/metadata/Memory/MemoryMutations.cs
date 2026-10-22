using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Memory;

public sealed partial class MemoryMetadataStore
{
    private static ImmutableArray<MetadataSelector> Parents(MetadataRecord value) => value switch
    {
        MetadataRegistry { PolicyId: MetadataOption<MetadataId>.Some policy } => [new MetadataSelector.Policy(policy.Value)],
        MetadataPackage package => [new MetadataSelector.Registry(package.Key.RegistryId)],
        MetadataPolicy { Scope: MetadataPolicyScope.Registry scope } => [new MetadataSelector.Registry(scope.Id)],
        MetadataCacheEntry entry => [new MetadataSelector.Registry(entry.Identity.RegistryId), new MetadataSelector.Package(entry.Package)],
        MetadataAccessAggregate aggregate => [new MetadataSelector.Registry(aggregate.Key.RegistryId)],
        _ => []
    };

    private static MemoryState Remove(MemoryState root, MetadataSelector key)
    {
        var dependents = root.Dependents;
        if (root.Records.TryGetValue(key, out var old))
        {
            foreach (var parent in Parents(old))
            {
                var remaining = dependents[parent].Remove(key);
                dependents = remaining.IsEmpty ? dependents.Remove(parent) : dependents.SetItem(parent, remaining);
            }
        }
        return root with { Records = root.Records.Remove(key), Dependents = dependents };
    }

    private static MemoryState Replace(MemoryState root, MetadataRecord record)
    {
        MetadataEncoding.Validate(record);
        root = Remove(root, record.Selector);
        var dependents = root.Dependents;
        foreach (var parent in Parents(record))
        {
            dependents = dependents.SetItem(parent, (dependents.TryGetValue(parent, out var existing)
                ? existing : ImmutableHashSet<MetadataSelector>.Empty).Add(record.Selector));
        }
        return root with { Records = root.Records.SetItem(record.Selector, record), Dependents = dependents };
    }

    private static void Expect(MemoryState root, MetadataSelector key, ExpectedRevision expected)
    {
        var exists = root.Records.TryGetValue(key, out var record);
        if (expected is ExpectedRevision.Absent && !exists
            || expected is ExpectedRevision.Match match && exists && record!.Revision == match.Revision) { return; }
        throw new MemoryContractFailure(MetadataFailureCode.Conflict);
    }

    private static MemoryState Reference(MemoryState root, ArtifactDigest digest, long delta)
    {
        var key = new MetadataSelector.Artifact(digest);
        if (!root.Records.TryGetValue(key, out var record) || record is not MetadataArtifactState artifact)
        { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
        var count = checked(artifact.LiveReferences + delta);
        if (count < 0) { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
        return Replace(root, artifact with { LiveReferences = count, Revision = new(Guid.NewGuid()) });
    }

    private static MemoryState Mutate(MemoryState root, MetadataMutation mutation, long now, HashSet<ArtifactDigest> touched)
    {
        var key = MetadataEncoding.Target(mutation);
        switch (mutation)
        {
            case MetadataMutation.PutRegistry put:
                Expect(root, key, put.Expected); return Replace(root, put.Record with { Revision = new(Guid.NewGuid()) });
            case MetadataMutation.PutPackage put:
                Expect(root, key, put.Expected); return Replace(root, put.Record with { Revision = new(Guid.NewGuid()) });
            case MetadataMutation.PutPolicy put:
                Expect(root, key, put.Expected); return Replace(root, put.Record with { Revision = new(Guid.NewGuid()) });
            case MetadataMutation.DeleteRegistry delete: Expect(root, key, new ExpectedRevision.Match(delete.Revision)); return Remove(root, key);
            case MetadataMutation.DeletePackage delete: Expect(root, key, new ExpectedRevision.Match(delete.Revision)); return Remove(root, key);
            case MetadataMutation.DeletePolicy delete: Expect(root, key, new ExpectedRevision.Match(delete.Revision)); return Remove(root, key);
            case MetadataMutation.DeleteAggregate delete: Expect(root, key, new ExpectedRevision.Match(delete.Revision)); return Remove(root, key);
            case MetadataMutation.PublishCacheEntry publication:
                {
                    Expect(root, key, publication.Expected);
                    if (root.Edges.TryGetValue(publication.Record.Identity, out var previous))
                    {
                        root = Reference(root, previous, -1);
                        touched.Add(previous);
                    }
                    var artifactKey = new MetadataSelector.Artifact(publication.Record.Digest);
                    if (root.Records.TryGetValue(artifactKey, out var old))
                    {
                        if (old is not MetadataArtifactState artifact || artifact.Length != publication.Record.Length)
                        { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                    }
                    else
                    {
                        root = Replace(root, new MetadataArtifactState
                        {
                            Digest = publication.Record.Digest,
                            Length = publication.Record.Length,
                            LiveReferences = 0,
                            Revision = new(Guid.NewGuid())
                        });
                    }
                    root = Replace(root, publication.Record with { Revision = new(Guid.NewGuid()) });
                    root = root with { Edges = root.Edges.SetItem(publication.Record.Identity, publication.Record.Digest) };
                    touched.Add(publication.Record.Digest);
                    return Reference(root, publication.Record.Digest, 1);
                }
            case MetadataMutation.DeleteCacheEntry deletion:
                {
                    Expect(root, key, new ExpectedRevision.Match(deletion.Revision));
                    if (!root.Edges.TryGetValue(deletion.Identity, out var digest))
                    { throw new MemoryContractFailure(MetadataFailureCode.CorruptState); }
                    root = root with { Edges = root.Edges.Remove(deletion.Identity) };
                    root = Remove(root, key);
                    touched.Add(digest);
                    return Reference(root, digest, -1);
                }
            case MetadataMutation.AddAggregateContribution contribution:
                {
                    var before = root.Records.TryGetValue(key, out var record) ? ((MetadataAccessAggregate)record).Counters : null;
                    var delta = contribution.Delta;
                    return Replace(root, new MetadataAccessAggregate
                    {
                        Key = contribution.Key,
                        Revision = new(Guid.NewGuid()),
                        Counters = new()
                        {
                            Hits = checked((before?.Hits ?? 0) + delta.Hits),
                            Misses = checked((before?.Misses ?? 0) + delta.Misses),
                            BytesServed = checked((before?.BytesServed ?? 0) + delta.BytesServed),
                            BytesFetched = checked((before?.BytesFetched ?? 0) + delta.BytesFetched),
                            LatencyMilliseconds = checked((before?.LatencyMilliseconds ?? 0) + delta.LatencyMilliseconds),
                            Samples = checked((before?.Samples ?? 0) + delta.Samples)
                        }
                    });
                }
            case MetadataMutation.AcquireLease acquisition:
                {
                    var old = root.Records.TryGetValue(key, out var record) ? (MetadataWorkLease)record : null;
                    if (old?.Owner is MetadataOption<MetadataId>.Some && now < old.Expires.UnixMilliseconds)
                    { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
                    return Replace(root, new MetadataWorkLease
                    {
                        Resource = acquisition.Resource,
                        Owner = new MetadataOption<MetadataId>.Some(acquisition.Owner),
                        Generation = checked((old?.Generation ?? 0) + 1),
                        Acquired = new(now),
                        Expires = new(checked(now + acquisition.TtlSeconds * 1000L)),
                        Revision = new(Guid.NewGuid())
                    });
                }
            case MetadataMutation.RenewLease renewal:
                {
                    var old = RequireOwned(root, renewal.Resource, renewal.Owner, renewal.Generation, renewal.Revision, now);
                    return Replace(root, old with { Acquired = new(now), Expires = new(checked(now + renewal.TtlSeconds * 1000L)), Revision = new(Guid.NewGuid()) });
                }
            case MetadataMutation.ReleaseLease release:
                {
                    var old = RequireOwned(root, release.Resource, release.Owner, release.Generation, release.Revision, now);
                    return Replace(root, old with { Owner = new MetadataOption<MetadataId>.None(), Revision = new(Guid.NewGuid()) });
                }
            case MetadataMutation.ConfirmUnreferenced: return root;
            default: throw new ArgumentException("Invalid metadata mutation.");
        }
    }

    private static MetadataWorkLease RequireOwned(MemoryState root, CanonicalText resource, MetadataId owner,
        long generation, MetadataRevision? revision, long now)
    {
        if (!root.Records.TryGetValue(new MetadataSelector.Lease(resource), out var record) || record is not MetadataWorkLease lease
            || lease.Owner is not MetadataOption<MetadataId>.Some current || current.Value != owner
            || lease.Generation != generation || revision is not null && lease.Revision != revision || now >= lease.Expires.UnixMilliseconds)
        { throw new MemoryContractFailure(MetadataFailureCode.Conflict); }
        return lease;
    }

    private static void ValidateGraph(MemoryState root, ImmutableArray<MetadataMutation> mutations, MemoryActivity activity)
    {
        foreach (var mutation in mutations)
        {
            activity.Check();
            var key = MetadataEncoding.Target(mutation);
            if (!root.Records.TryGetValue(key, out var record))
            {
                if (root.Dependents.TryGetValue(key, out var dependents) && !dependents.IsEmpty)
                { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                continue;
            }
            foreach (var parent in Parents(record))
            {
                if (!root.Records.ContainsKey(parent)) { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
            }
            switch (record)
            {
                case MetadataRegistry registry:
                    if (registry.PolicyId is MetadataOption<MetadataId>.Some policy
                        && root.Records[new MetadataSelector.Policy(policy.Value)] is MetadataPolicy { Scope: MetadataPolicyScope.Registry scope }
                        && scope.Id != registry.Id) { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                    if (root.Dependents.TryGetValue(key, out var children))
                    {
                        foreach (var child in children)
                        {
                            activity.Check();
                            if (root.Records[child] is MetadataPackage package && package.Key.Ecosystem != registry.Ecosystem
                                || root.Records[child] is MetadataCacheEntry entry && entry.Identity.Ecosystem != registry.Ecosystem)
                            { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                        }
                    }
                    break;
                case MetadataPackage package:
                    if (((MetadataRegistry)root.Records[new MetadataSelector.Registry(package.Key.RegistryId)]).Ecosystem != package.Key.Ecosystem)
                    { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                    break;
                case MetadataCacheEntry entry:
                    var parentRegistry = (MetadataRegistry)root.Records[new MetadataSelector.Registry(entry.Identity.RegistryId)];
                    if (!parentRegistry.Enabled || parentRegistry.Ecosystem != entry.Identity.Ecosystem)
                    { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                    break;
                case MetadataPolicy { Scope: MetadataPolicyScope.Registry policyScope }:
                    if (root.Dependents.TryGetValue(key, out var linkedRegistries))
                    {
                        foreach (var child in linkedRegistries)
                        {
                            activity.Check();
                            if (child != new MetadataSelector.Registry(policyScope.Id))
                            { throw new MemoryContractFailure(MetadataFailureCode.InvalidInput); }
                        }
                    }
                    break;
            }
        }
    }
}
