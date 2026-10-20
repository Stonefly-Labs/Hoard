namespace Hoard.Abstractions.Modules;

public sealed record CapabilityDeclaration
{
    public required string Id { get; init; }
    public required string Version { get; init; }
    public required string Description { get; init; }
}
