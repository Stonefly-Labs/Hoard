using System.Collections.Immutable;

namespace Hoard.Hosting.Composition;

public sealed record HoardStartupSelection
{
    public required ImmutableArray<string> EnabledModuleIds { get; init; }
    public required string MetadataModuleId { get; init; }
    public required string ArtifactModuleId { get; init; }
    public required ImmutableArray<HoardRequiredCapability> RequiredCapabilities { get; init; }
}
