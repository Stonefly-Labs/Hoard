namespace Hoard.Abstractions.Modules;

public sealed record ConfigurationRequirement
{
    public required string Key { get; init; }
    public required string Description { get; init; }
    public required bool Required { get; init; }
    public required bool SecretReference { get; init; }
}
