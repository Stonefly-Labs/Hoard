using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;

namespace Hoard.Fixtures.Protocol;

public sealed class ProtocolProvider : IProtocolProvider
{
    public static ModuleDescriptor Declaration { get; } = new()
    {
        Id = "fixture.protocol",
        Category = ModuleCategory.Protocol,
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
