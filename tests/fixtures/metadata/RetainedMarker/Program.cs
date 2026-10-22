using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddHoard().AddModule<RetainedMetadataProvider>(RetainedMetadataProvider.Declaration);
using var container = services.BuildServiceProvider();
var registration = container.GetServices<HoardModuleRegistration>().Single();
if (registration.ProviderType != typeof(RetainedMetadataProvider)
    || registration.Declaration != RetainedMetadataProvider.Declaration
    || typeof(IMetadataProvider).GetMethods().Length != 0)
{
    throw new InvalidOperationException("Retained marker registration changed.");
}
Console.WriteLine("metadata-marker-compatible");

internal sealed class RetainedMetadataProvider : IMetadataProvider
{
    public static ModuleDescriptor Declaration { get; } = new()
    {
        Id = "fixture.metadata.retained",
        Category = ModuleCategory.Metadata,
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
