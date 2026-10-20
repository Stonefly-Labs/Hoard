namespace Hoard.Abstractions.Modules;

public sealed record ModuleDependency
{
    public required string ModuleId { get; init; }
    public required string VersionRange { get; init; }
    public required bool Optional { get; init; }
    public required bool AllowPrerelease { get; init; }
}
