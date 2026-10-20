using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
var builder = services.AddHoard();
var declaration = new ModuleDescriptor
{
    Id = "legacy.protocol",
    Category = ModuleCategory.Protocol,
    Version = "0.1.0",
    Compatibility = new() { HostRange = "[0.1.0,0.2.0)", AbstractionsRange = "[0.1.0,0.2.0)", AllowPrereleaseHost = false, AllowPrereleaseAbstractions = false },
    Dependencies = [],
    Capabilities = [],
    Configuration = [],
    Endpoints = [],
    Health = [],
    Provenance = new() { Publisher = "Registration compatibility fixture", SupportStatus = ModuleSupportStatus.Fixture }
};
builder.AddModule<LegacyProvider>(declaration);
var registration = services.Single().ImplementationInstance as HoardModuleRegistration;
if (!ReferenceEquals(builder.Services, services) || registration?.Declaration != declaration
    || registration.ProviderType != typeof(LegacyProvider))
{ throw new InvalidOperationException("Registration compatibility failed."); }
Console.WriteLine("registration-compatible");

sealed class LegacyProvider(string requiredArgument) : IProtocolProvider
{
    public string Argument { get; } = requiredArgument;
}
