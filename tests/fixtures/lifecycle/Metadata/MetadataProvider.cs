using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;

namespace Hoard.Fixtures.Lifecycle.Metadata;

public sealed class MetadataProvider : IMetadataProvider
{
    public static int Acquisitions;
    public static int Releases;
    public static int ConnectionAttempts;
    public static ModuleDescriptor Declaration => new()
    {
        Id = "fixture.metadata",
        Category = ModuleCategory.Metadata,
        Version = "0.1.0",
        Compatibility = new() { HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
        Dependencies = [],
        Capabilities = [],
        Configuration = [],
        Endpoints = [],
        Health = [],
        Provenance = new() { Publisher = "Hoard lifecycle acceptance", SupportStatus = ModuleSupportStatus.Fixture }
    };
    public void Acquire()
    {
        Interlocked.Increment(ref ConnectionAttempts);
        Interlocked.Increment(ref Acquisitions);
    }
    public void Release() => Interlocked.Increment(ref Releases);
}
