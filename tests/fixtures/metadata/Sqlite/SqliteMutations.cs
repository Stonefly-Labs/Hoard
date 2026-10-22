using Hoard.Abstractions.Metadata;

namespace Hoard.Fixtures.Metadata.Sqlite;

public sealed partial class SqliteMetadataStore
{
    private static void Expect(MetadataRecord? existing, ExpectedRevision expected)
    {
        if (expected is ExpectedRevision.Absent && existing is null
            || expected is ExpectedRevision.Match match && existing?.Revision == match.Revision) { return; }
        throw new SqliteContractFailure(MetadataFailureCode.Conflict);
    }

    private void Delete(MetadataSelector key, MetadataRevision expected)
    {
        Expect(Get(key), new ExpectedRevision.Match(expected));
        SqliteStatement.Execute(Database, "DELETE FROM metadata_records WHERE key=?1", RecordKey(key));
    }

    private void Apply(MetadataMutation mutation, long now, HashSet<ArtifactDigest> touched)
    {
        switch (mutation)
        {
            case MetadataMutation.PutRegistry put:
                Expect(Get(put.Record.Selector), put.Expected); Put(put.Record with { Revision = NewRevision() }); break;
            case MetadataMutation.PutPackage put:
                Expect(Get(put.Record.Selector), put.Expected); Put(put.Record with { Revision = NewRevision() }); break;
            case MetadataMutation.PutPolicy put:
                Expect(Get(put.Record.Selector), put.Expected); Put(put.Record with { Revision = NewRevision() }); break;
            case MetadataMutation.DeleteRegistry delete: Delete(new MetadataSelector.Registry(delete.Id), delete.Revision); break;
            case MetadataMutation.DeletePackage delete: Delete(new MetadataSelector.Package(delete.Key), delete.Revision); break;
            case MetadataMutation.DeletePolicy delete: Delete(new MetadataSelector.Policy(delete.Id), delete.Revision); break;
            case MetadataMutation.PublishCacheEntry publish:
                {
                    var old = Get(publish.Record.Selector);
                    Expect(old, publish.Expected);
                    if (old is MetadataCacheEntry prior) { touched.Add(prior.Digest); }
                    var artifact = Get(new MetadataSelector.Artifact(publish.Record.Digest));
                    if (artifact is MetadataArtifactState existing && existing.Length != publish.Record.Length)
                    { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                    if (artifact is null)
                    {
                        Put(new MetadataArtifactState
                        {
                            Digest = publish.Record.Digest,
                            Length = publish.Record.Length,
                            LiveReferences = 0,
                            Revision = NewRevision()
                        });
                    }
                    Put(publish.Record with { Revision = NewRevision() });
                    SqliteStatement.Execute(Database, "INSERT INTO metadata_edges(entry,digest) VALUES(?1,?2) ON CONFLICT(entry) DO UPDATE SET digest=excluded.digest",
                        RecordKey(publish.Record.Selector), RecordKey(new MetadataSelector.Artifact(publish.Record.Digest)));
                    touched.Add(publish.Record.Digest);
                    break;
                }
            case MetadataMutation.DeleteCacheEntry delete:
                {
                    var key = new MetadataSelector.CacheEntry(delete.Identity);
                    if (Get(key) is MetadataCacheEntry prior) { touched.Add(prior.Digest); }
                    SqliteStatement.Execute(Database, "DELETE FROM metadata_edges WHERE entry=?1", RecordKey(key));
                    Delete(key, delete.Revision);
                    break;
                }
            case MetadataMutation.AddAggregateContribution add:
                {
                    var key = new MetadataSelector.Aggregate(add.Key);
                    var existing = Get(key) as MetadataAccessAggregate;
                    var before = existing?.Counters;
                    var after = new MetadataAggregateDelta
                    {
                        Hits = checked((before?.Hits ?? 0) + add.Delta.Hits),
                        Misses = checked((before?.Misses ?? 0) + add.Delta.Misses),
                        BytesServed = checked((before?.BytesServed ?? 0) + add.Delta.BytesServed),
                        BytesFetched = checked((before?.BytesFetched ?? 0) + add.Delta.BytesFetched),
                        LatencyMilliseconds = checked((before?.LatencyMilliseconds ?? 0) + add.Delta.LatencyMilliseconds),
                        Samples = checked((before?.Samples ?? 0) + add.Delta.Samples)
                    };
                    Put(new MetadataAccessAggregate { Key = add.Key, Counters = after, Revision = NewRevision() });
                    break;
                }
            case MetadataMutation.DeleteAggregate delete: Delete(new MetadataSelector.Aggregate(delete.Key), delete.Revision); break;
            case MetadataMutation.AcquireLease acquire:
                {
                    var old = Get(new MetadataSelector.Lease(acquire.Resource)) as MetadataWorkLease;
                    if (old?.Owner is MetadataOption<MetadataId>.Some && now < old.Expires.UnixMilliseconds)
                    { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
                    Put(new MetadataWorkLease
                    {
                        Resource = acquire.Resource,
                        Owner = new MetadataOption<MetadataId>.Some(acquire.Owner),
                        Generation = checked((old?.Generation ?? 0) + 1),
                        Acquired = new(now),
                        Expires = new(checked(now + acquire.TtlSeconds * 1000L)),
                        Revision = NewRevision()
                    });
                    break;
                }
            case MetadataMutation.RenewLease renew:
                {
                    var old = OwnedLease(renew.Resource, renew.Owner, renew.Generation, renew.Revision, now);
                    Put(old with { Acquired = new(now), Expires = new(checked(now + renew.TtlSeconds * 1000L)), Revision = NewRevision() });
                    break;
                }
            case MetadataMutation.ReleaseLease release:
                {
                    var old = OwnedLease(release.Resource, release.Owner, release.Generation, release.Revision, now);
                    Put(old with { Owner = new MetadataOption<MetadataId>.None(), Revision = NewRevision() });
                    break;
                }
            case MetadataMutation.ConfirmUnreferenced: break;
            default: throw new ArgumentException("Invalid metadata mutation.");
        }
    }

    private MetadataWorkLease OwnedLease(CanonicalText resource, MetadataId owner, long generation, MetadataRevision? revision, long now)
    {
        if (Get(new MetadataSelector.Lease(resource)) is not MetadataWorkLease lease
            || lease.Owner is not MetadataOption<MetadataId>.Some current || current.Value != owner
            || lease.Generation != generation || revision is not null && lease.Revision != revision
            || now >= lease.Expires.UnixMilliseconds)
        { throw new SqliteContractFailure(MetadataFailureCode.Conflict); }
        return lease;
    }

    private void CheckLeaseGuard(MetadataOption<MetadataLeaseGuard> guard, long now)
    {
        if (guard is MetadataOption<MetadataLeaseGuard>.Some some)
        { _ = OwnedLease(some.Value.Resource, some.Value.Owner, some.Value.Generation, null, now); }
    }

    private void UpdateReferenceCount(ArtifactDigest digest)
    {
        var key = new MetadataSelector.Artifact(digest);
        var artifact = Get(key) as MetadataArtifactState ?? throw new SqliteNativeFailure(11);
        using var count = new SqliteStatement(Database, "SELECT count(*) FROM metadata_edges WHERE digest=?1", RecordKey(key));
        if (!count.Step()) { throw new SqliteNativeFailure(11); }
        Put(artifact with { LiveReferences = count.Number(0), Revision = NewRevision() });
    }

    private void CheckFinalGraph(MetadataMutation mutation)
    {
        var key = MetadataEncoding.Target(mutation);
        var record = Get(key);
        switch (record)
        {
            case MetadataRegistry registry:
                if (registry.PolicyId is MetadataOption<MetadataId>.Some policy
                    && (Get(new MetadataSelector.Policy(policy.Value)) is not MetadataPolicy linked
                        || linked.Scope is MetadataPolicyScope.Registry scope && scope.Id != registry.Id))
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                if (Exists("SELECT 1 FROM metadata_records WHERE registry=?1 AND kind IN(2,4) AND ecosystem<>?2 LIMIT 1",
                    IdBytes(registry.Id), System.Text.Encoding.UTF8.GetBytes(registry.Ecosystem.Value)))
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                break;
            case MetadataPackage package:
                if (Get(new MetadataSelector.Registry(package.Key.RegistryId)) is not MetadataRegistry parent
                    || parent.Ecosystem != package.Key.Ecosystem)
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                break;
            case MetadataPolicy { Scope: MetadataPolicyScope.Registry policyScope } scopedPolicy:
                if (Get(new MetadataSelector.Registry(policyScope.Id)) is null
                    || Exists("SELECT 1 FROM metadata_records WHERE policy=?1 AND key<>?2 LIMIT 1",
                        RecordKey(scopedPolicy.Selector), RecordKey(new MetadataSelector.Registry(policyScope.Id))))
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                break;
            case MetadataCacheEntry entry:
                if (Get(new MetadataSelector.Registry(entry.Identity.RegistryId)) is not MetadataRegistry entryRegistry
                    || !entryRegistry.Enabled || entryRegistry.Ecosystem != entry.Identity.Ecosystem
                    || Get(new MetadataSelector.Package(entry.Package)) is null)
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                break;
            case MetadataAccessAggregate aggregate:
                if (Get(new MetadataSelector.Registry(aggregate.Key.RegistryId)) is null)
                { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
                break;
        }
        if (record is null)
        {
            var referenced = key switch
            {
                MetadataSelector.Registry registry => Exists("SELECT 1 FROM metadata_records WHERE registry=?1 LIMIT 1", IdBytes(registry.Id)),
                MetadataSelector.Package => Exists("SELECT 1 FROM metadata_records WHERE package=?1 LIMIT 1", RecordKey(key)),
                MetadataSelector.Policy => Exists("SELECT 1 FROM metadata_records WHERE policy=?1 LIMIT 1", RecordKey(key)),
                _ => false
            };
            if (referenced) { throw new SqliteContractFailure(MetadataFailureCode.InvalidInput); }
        }
    }
}
