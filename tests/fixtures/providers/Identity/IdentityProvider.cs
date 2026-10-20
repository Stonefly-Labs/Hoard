using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;

namespace Hoard.Fixtures.Identity;

public sealed class IdentityProvider : IIdentityProvider
{
    public static ModuleDescriptor Declaration { get; } = new()
    {
        Id = "fixture.identity",
        Category = ModuleCategory.Identity,
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
