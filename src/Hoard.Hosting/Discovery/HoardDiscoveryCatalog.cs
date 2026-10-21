using System.Collections.Immutable;
using Hoard.Abstractions.Modules;

namespace Hoard.Hosting.Discovery;

public sealed record HoardDiscoveryCatalog(string DistributionId, string DistributionVersion, string InventoryCompleteness)
{
    public ImmutableArray<ModuleDescriptor> IncludedModules { get; init; } = [];
    public ImmutableArray<DiscoveryPublicationPolicy> Publications { get; init; } = [];
    public ImmutableArray<DiscoveryContribution> Contributions { get; init; } = [];
    public ImmutableArray<DiscoveryServiceBinding> ServiceBindings { get; init; } = [];
}

public sealed record DiscoveryContribution(string CapabilityId, string Version, string OperationId,
    ImmutableArray<string> Owners)
{
    public ImmutableArray<string> Dependencies { get; init; } = [];
    public ImmutableArray<DiscoveryRouteBinding> Routes { get; init; } = [];
    public ImmutableArray<string> Services { get; init; } = [];
    public string Support { get; init; } = "unverified";
    public string EvidenceScope { get; init; } = "unknown";
    public ImmutableArray<string> EvidenceIds { get; init; } = [];
}

public sealed record DiscoveryRouteBinding(string OwnerId, string ResponsibilityId, string Method);
public sealed record DiscoveryServiceBinding(string Id, string OwnerId, Type ServiceType);
