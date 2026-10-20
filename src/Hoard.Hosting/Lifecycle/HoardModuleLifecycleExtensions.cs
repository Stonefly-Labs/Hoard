using Hoard.Abstractions.Providers;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Lifecycle;

public static class HoardModuleLifecycleExtensions
{
    public static HoardBuilder AddModuleLifecycle<TProvider, TModule>(this HoardBuilder builder)
        where TProvider : class, IHoardProvider
        where TModule : class, IHoardModule, new()
    {
        ArgumentNullException.ThrowIfNull(builder);
        builder.Services.AddSingleton(new HoardModuleLifecycleRegistration(typeof(TProvider), typeof(TModule)));
        return builder;
    }
}
