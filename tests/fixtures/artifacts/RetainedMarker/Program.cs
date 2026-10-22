using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddHoard().AddModule<RetainedArtifactProvider>(RetainedArtifactProvider.Declaration);
using var container = services.BuildServiceProvider();
var registration = container.GetServices<HoardModuleRegistration>().Single();
if (registration.ProviderType != typeof(RetainedArtifactProvider)
    || registration.Declaration != RetainedArtifactProvider.Declaration
    || typeof(IArtifactProvider).GetMethods().Length != 0
    || new ArtifactDigest(new string('a', 64)).Hex != new string('a', 64))
{
    throw new InvalidOperationException("Retained artifact contract changed.");
}
Console.WriteLine("artifact-marker-compatible");

internal sealed class RetainedArtifactProvider : IArtifactProvider
{
    public static ModuleDescriptor Declaration { get; } = new()
    {
        Id = "fixture.artifact.retained",
        Category = ModuleCategory.Artifact,
        Version = "0.1.0",
        Compatibility = new()
        {
            HostRange = "[0.1.0,0.2.0)",
            AbstractionsRange = "[0.1.0,0.2.0)",
            AllowPrereleaseHost = false,
            AllowPrereleaseAbstractions = false
        },
        Dependencies = [],
        Capabilities = [],
        Configuration = [],
        Endpoints = [],
        Health = [],
        Provenance = new() { Publisher = "Hoard test fixtures", SupportStatus = ModuleSupportStatus.Fixture }
    };
}
