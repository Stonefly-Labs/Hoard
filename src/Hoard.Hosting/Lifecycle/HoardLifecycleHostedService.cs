using Microsoft.Extensions.Hosting;

namespace Hoard.Hosting.Lifecycle;

internal sealed class HoardLifecycleHostedService(IHoardLifecycle lifecycle, IHostApplicationLifetime lifetime) : IHostedService
{
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        using var registration = cancellationToken.Register(() => { _ = lifecycle.StopAsync(); });
        lifetime.ApplicationStopping.Register(() => { _ = lifecycle.StopAsync(); });
        if (!(await lifecycle.StartAsync(cancellationToken).ConfigureAwait(false)).Ready)
        { throw new HoardLifecycleException(lifecycle.Snapshot.Diagnostics); }
    }

    public async Task StopAsync(CancellationToken cancellationToken) =>
        await lifecycle.StopAsync(cancellationToken).ConfigureAwait(false);
}
