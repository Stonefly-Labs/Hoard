namespace Hoard.Abstractions.Modules;

public sealed record HealthResponsibility
{
    public required string Id { get; init; }
    public required string Description { get; init; }
    public required bool RequiredForReadiness { get; init; }
}
