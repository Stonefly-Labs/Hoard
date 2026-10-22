using System.Collections.Immutable;
using System.Text.Json.Serialization;

namespace Hoard.Abstractions.Metadata;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$selector")]
[JsonDerivedType(typeof(MetadataSelector.Registry), "registry")]
[JsonDerivedType(typeof(MetadataSelector.Package), "package")]
[JsonDerivedType(typeof(MetadataSelector.Policy), "policy")]
[JsonDerivedType(typeof(MetadataSelector.CacheEntry), "entry")]
[JsonDerivedType(typeof(MetadataSelector.Artifact), "artifact")]
[JsonDerivedType(typeof(MetadataSelector.Lease), "lease")]
[JsonDerivedType(typeof(MetadataSelector.Aggregate), "aggregate")]
public abstract record MetadataSelector : MetadataDiagnostic
{
    private MetadataSelector() { }
    public sealed record Registry(MetadataId Id) : MetadataSelector;
    public sealed record Package(MetadataPackageKey Key) : MetadataSelector;
    public sealed record Policy(MetadataId Id) : MetadataSelector;
    public sealed record CacheEntry(MetadataRequestIdentity Identity) : MetadataSelector;
    public sealed record Artifact(ArtifactDigest Digest) : MetadataSelector;
    public sealed record Lease(CanonicalText Resource) : MetadataSelector;
    public sealed record Aggregate(MetadataAggregateKey Key) : MetadataSelector;
}

public sealed record MetadataReadGroup : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataReadGroup(ImmutableArray<MetadataSelector> selectors)
    {
        Selectors = MetadataValidation.Collection(selectors, 1, 64);
        MetadataValidation.Require(selectors.All(selector => selector is not null));
    }
    public ImmutableArray<MetadataSelector> Selectors { get; }
}

public sealed record MetadataLeaseGuard(CanonicalText Resource, MetadataId Owner, long Generation) : MetadataDiagnostic;
public sealed record MetadataOperationTicket(
    MetadataId Epoch, MetadataId Id, MetadataInstant Issued, MetadataInstant Expires) : MetadataDiagnostic;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$mutation")]
[JsonDerivedType(typeof(MetadataMutation.PutRegistry), "put-registry")]
[JsonDerivedType(typeof(MetadataMutation.PutPackage), "put-package")]
[JsonDerivedType(typeof(MetadataMutation.PutPolicy), "put-policy")]
[JsonDerivedType(typeof(MetadataMutation.DeleteRegistry), "delete-registry")]
[JsonDerivedType(typeof(MetadataMutation.DeletePackage), "delete-package")]
[JsonDerivedType(typeof(MetadataMutation.DeletePolicy), "delete-policy")]
[JsonDerivedType(typeof(MetadataMutation.PublishCacheEntry), "publish-entry")]
[JsonDerivedType(typeof(MetadataMutation.DeleteCacheEntry), "delete-entry")]
[JsonDerivedType(typeof(MetadataMutation.AddAggregateContribution), "add-aggregate")]
[JsonDerivedType(typeof(MetadataMutation.DeleteAggregate), "delete-aggregate")]
[JsonDerivedType(typeof(MetadataMutation.AcquireLease), "acquire-lease")]
[JsonDerivedType(typeof(MetadataMutation.RenewLease), "renew-lease")]
[JsonDerivedType(typeof(MetadataMutation.ReleaseLease), "release-lease")]
[JsonDerivedType(typeof(MetadataMutation.ConfirmUnreferenced), "confirm-unreferenced")]
public abstract record MetadataMutation : MetadataDiagnostic
{
    private MetadataMutation() { }
    public sealed record PutRegistry(MetadataRegistry Record, ExpectedRevision Expected) : MetadataMutation;
    public sealed record PutPackage(MetadataPackage Record, ExpectedRevision Expected) : MetadataMutation;
    public sealed record PutPolicy(MetadataPolicy Record, ExpectedRevision Expected) : MetadataMutation;
    public sealed record DeleteRegistry(MetadataId Id, MetadataRevision Revision) : MetadataMutation;
    public sealed record DeletePackage(MetadataPackageKey Key, MetadataRevision Revision) : MetadataMutation;
    public sealed record DeletePolicy(MetadataId Id, MetadataRevision Revision) : MetadataMutation;
    public sealed record PublishCacheEntry(
        MetadataCacheEntry Record, ExpectedRevision Expected, MetadataArtifactEvidence Evidence) : MetadataMutation;
    public sealed record DeleteCacheEntry(MetadataRequestIdentity Identity, MetadataRevision Revision) : MetadataMutation;
    public sealed record AddAggregateContribution(MetadataAggregateKey Key, MetadataAggregateDelta Delta) : MetadataMutation;
    public sealed record DeleteAggregate(MetadataAggregateKey Key, MetadataRevision Revision) : MetadataMutation;
    public sealed record AcquireLease(CanonicalText Resource, MetadataId Owner, int TtlSeconds) : MetadataMutation;
    public sealed record RenewLease(
        CanonicalText Resource, MetadataId Owner, long Generation, MetadataRevision Revision, int TtlSeconds) : MetadataMutation;
    public sealed record ReleaseLease(
        CanonicalText Resource, MetadataId Owner, long Generation, MetadataRevision Revision) : MetadataMutation;
    public sealed record ConfirmUnreferenced(ArtifactDigest Digest, MetadataRevision ReferenceRevision) : MetadataMutation;
}

public sealed record MetadataMutationBatch : MetadataDiagnostic
{
    [JsonConstructor]
    public MetadataMutationBatch(MetadataOperationTicket ticket, ImmutableArray<MetadataMutation> mutations,
        MetadataOption<MetadataLeaseGuard> leaseGuard)
    {
        ArgumentNullException.ThrowIfNull(ticket);
        ArgumentNullException.ThrowIfNull(leaseGuard);
        Mutations = MetadataValidation.Collection(mutations, 1, 64);
        MetadataValidation.Require(mutations.All(mutation => mutation is not null));
        Ticket = ticket;
        LeaseGuard = leaseGuard;
    }
    public MetadataOperationTicket Ticket { get; }
    public ImmutableArray<MetadataMutation> Mutations { get; }
    public MetadataOption<MetadataLeaseGuard> LeaseGuard { get; }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "$query")]
[JsonDerivedType(typeof(MetadataPageQuery.Registries), "registries")]
[JsonDerivedType(typeof(MetadataPageQuery.Packages), "packages")]
[JsonDerivedType(typeof(MetadataPageQuery.CacheEntries), "entries")]
[JsonDerivedType(typeof(MetadataPageQuery.Policies), "policies")]
[JsonDerivedType(typeof(MetadataPageQuery.Aggregates), "aggregates")]
[JsonDerivedType(typeof(MetadataPageQuery.Leases), "leases")]
[JsonDerivedType(typeof(MetadataPageQuery.Artifacts), "artifacts")]
public abstract record MetadataPageQuery : MetadataDiagnostic
{
    private MetadataPageQuery() { }
    public required int PageSize { get; init; }
    public required MetadataOption<MetadataContinuation> Continuation { get; init; }
    public sealed record Registries : MetadataPageQuery;
    public sealed record Packages(MetadataId RegistryId) : MetadataPageQuery;
    public sealed record CacheEntries(
        MetadataId RegistryId, CanonicalText AuthorizationPartition, MetadataOption<MetadataPackageKey> Package) : MetadataPageQuery;
    public sealed record Policies(MetadataPolicyScope Scope) : MetadataPageQuery;
    public sealed record Aggregates(
        MetadataId RegistryId, CanonicalText AuthorizationPartition, MetadataInstant Start, MetadataInstant End) : MetadataPageQuery;
    public sealed record Leases(CanonicalText ResourcePrefix) : MetadataPageQuery;
    public sealed record Artifacts : MetadataPageQuery;
}

public sealed record MetadataCallOptions(TimeSpan? Timeout = null) : MetadataDiagnostic
{
    public TimeSpan EffectiveTimeout => Timeout ?? TimeSpan.FromSeconds(5);
}

public sealed record MetadataAdministrationOptions(TimeSpan? Timeout = null) : MetadataDiagnostic
{
    public TimeSpan EffectiveTimeout => Timeout ?? TimeSpan.FromSeconds(30);
}
