using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;

namespace Hoard.Fixtures.Configuration.LegacyOptions;

public sealed class LegacyOptionsProvider : IMetadataProvider
{
    public static ModuleDescriptor Declaration { get; } = new()
    {
        Id = "fixture.legacy-options",
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
        Configuration =
        [
            new() { Key = "label", Description = "Fixture ordinary label.", Required = true, SecretReference = false },
            new() { Key = "credential", Description = "Fixture credential reference.", Required = true, SecretReference = true }
        ],
        Endpoints = [],
        Health = [],
        Provenance = new() { Publisher = "Configuration fixtures", SupportStatus = ModuleSupportStatus.Fixture }
    };

    public bool Accepts(string label, string credential) =>
        label == "configured-old-provider" && credential == "invented-configuration-credential";
}
