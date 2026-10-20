using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting;

public static class HoardServiceCollectionExtensions
{
    public static HoardBuilder AddHoard(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);
        return new(services);
    }
}
