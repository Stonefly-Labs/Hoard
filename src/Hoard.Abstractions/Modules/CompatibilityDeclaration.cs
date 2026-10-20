namespace Hoard.Abstractions.Modules;

public sealed record CompatibilityDeclaration
{
    public required string HostRange { get; init; }
    public required string AbstractionsRange { get; init; }
    public required bool AllowPrereleaseHost { get; init; }
    public required bool AllowPrereleaseAbstractions { get; init; }
}
