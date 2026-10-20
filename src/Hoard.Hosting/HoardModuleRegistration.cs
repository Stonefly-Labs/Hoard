using Hoard.Abstractions.Modules;

namespace Hoard.Hosting;

public sealed record HoardModuleRegistration
{
    public required ModuleDescriptor Declaration { get; init; }
    public required Type ProviderType { get; init; }
}
