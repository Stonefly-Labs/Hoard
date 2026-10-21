using System.Collections.Immutable;

namespace Hoard.Hosting.Discovery;

public sealed record DiscoveryPublicationPolicy(string ModuleId)
{
    public string? Publisher { get; init; }
    public ImmutableArray<DiscoveryPublicOption> Options { get; init; } = [];
}

public sealed record DiscoveryPublicOption(string Id)
{
    public string? Description { get; init; }
    public string? PublicDefault { get; init; }
    public ImmutableArray<string> AllowedValues { get; init; } = [];
}
