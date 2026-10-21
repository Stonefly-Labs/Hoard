using Hoard.Abstractions.Providers;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Configuration;

internal sealed record ConfigurationRegistration(Type ProviderType,
    HoardModuleConfiguration Contract, HoardOptionValidator? Validator);

public static class HoardModuleConfigurationExtensions
{
    public static HoardBuilder AddModuleConfiguration<TProvider>(this HoardBuilder builder,
        HoardModuleConfiguration contract, HoardOptionValidator? validator = null)
        where TProvider : class, IHoardProvider
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(contract);
        lock (builder.ConfigurationGate)
        { builder.Services.AddSingleton(new ConfigurationRegistration(typeof(TProvider), contract, validator)); }
        return builder;
    }
}
