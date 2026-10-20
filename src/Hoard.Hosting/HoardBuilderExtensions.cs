using Hoard.Abstractions.Modules;
using Hoard.Abstractions.Providers;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting;

public static class HoardBuilderExtensions
{
    public static HoardBuilder AddModule<TProvider>(this HoardBuilder builder, ModuleDescriptor declaration)
        where TProvider : class, IHoardProvider
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(declaration);
        builder.Services.AddSingleton(new HoardModuleRegistration
        {
            Declaration = declaration,
            ProviderType = typeof(TProvider)
        });
        return builder;
    }
}
