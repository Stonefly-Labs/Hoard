using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;

namespace FixtureIdentity;

public sealed class Provider : IIdentityProvider
{
    public static HoardBuilder Register(HoardBuilder builder, ModuleDescriptor declaration) =>
        builder.AddModule<Provider>(declaration);
}
