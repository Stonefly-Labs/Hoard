namespace Hoard.Abstractions.Modules;

public sealed record ModuleProvenance
{
    public required string Publisher { get; init; }
    public required ModuleSupportStatus SupportStatus { get; init; }
    public Uri? SourceUrl { get; init; }
    public Uri? SupportUrl { get; init; }
}
