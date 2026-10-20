namespace Hoard.Abstractions.Modules;

public sealed record EndpointResponsibility
{
    public required string Id { get; init; }
    public required string Description { get; init; }
}
