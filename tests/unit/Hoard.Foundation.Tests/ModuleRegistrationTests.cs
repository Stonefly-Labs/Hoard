using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Hoard.Hosting;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Foundation.Tests;

public class ModuleRegistrationTests
{
    private static ModuleDescriptor Declaration => new()
    {
        Id = "fixture.throwing",
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
        Provenance = new() { Publisher = "Hoard tests", SupportStatus = ModuleSupportStatus.Fixture }
    };

    private sealed class ThrowingProvider : IProtocolProvider
    {
        public ThrowingProvider(string notResolved) => throw new InvalidOperationException("Provider must never be constructed.");
    }

    [Fact]
    public void Metadata_and_repeated_registrations_do_not_activate_or_install_provider_services()
    {
        IServiceCollection services = new ServiceCollection();
        services.Add(ServiceDescriptor.Singleton(typeof(string), "existing"));
        var original = services[0];
        var builder = services.AddHoard();
        Assert.Same(services, builder.Services);
        Assert.Single(services);
        var declaration = Declaration;
        Assert.Equal("fixture.throwing", declaration.Id);
        Assert.Same(builder, builder.AddModule<ThrowingProvider>(declaration));
        builder.AddModule<ThrowingProvider>(declaration);
        Assert.Equal(3, services.Count);
        Assert.Same(original, services[0]);
        Assert.All(services.Skip(1), descriptor =>
        {
            Assert.Equal(typeof(HoardModuleRegistration), descriptor.ServiceType);
            Assert.Null(descriptor.ImplementationFactory);
            Assert.Null(descriptor.ImplementationType);
            var registration = Assert.IsType<HoardModuleRegistration>(descriptor.ImplementationInstance);
            Assert.Same(declaration, registration.Declaration);
            Assert.Equal(typeof(ThrowingProvider), registration.ProviderType);
        });
    }

    [Fact]
    public void Null_arguments_are_explicit_errors_with_no_fallback()
    {
        Assert.Equal("services", Assert.Throws<ArgumentNullException>(() =>
            HoardServiceCollectionExtensions.AddHoard(null!)).ParamName);
        Assert.Equal("builder", Assert.Throws<ArgumentNullException>(() =>
            HoardBuilderExtensions.AddModule<ThrowingProvider>(null!, Declaration)).ParamName);
        var builder = new ServiceCollection().AddHoard();
        Assert.Equal("declaration", Assert.Throws<ArgumentNullException>(() =>
            builder.AddModule<ThrowingProvider>(null!)).ParamName);
        Assert.Empty(builder.Services);
    }
}
