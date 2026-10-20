using System.Collections.Immutable;

namespace Hoard.Abstractions.Modules;

public sealed record ModuleDescriptor
{
    public required string Id { get; init; }
    public required ModuleCategory Category { get; init; }
    public required string Version { get; init; }
    public required CompatibilityDeclaration Compatibility { get; init; }
    public required ImmutableArray<ModuleDependency> Dependencies { get; init; }
    public required ImmutableArray<CapabilityDeclaration> Capabilities { get; init; }
    public required ImmutableArray<ConfigurationRequirement> Configuration { get; init; }
    public required ImmutableArray<EndpointResponsibility> Endpoints { get; init; }
    public required ImmutableArray<HealthResponsibility> Health { get; init; }
    public required ModuleProvenance Provenance { get; init; }
}
