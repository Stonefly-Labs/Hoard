using Hoard.Hosting.Composition;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Hoard.Hosting.Lifecycle;

public static class HoardServiceCompositionExtensions
{
    public static async Task<HoardServiceComposition> ComposeHoardModulesAsync(this HoardBuilder builder,
        HoardValidatedComposition composition, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(composition);
        lock (composition)
        {
            if (composition.Consumed || !ReferenceEquals(builder, composition.Builder)
                || !builder.Services.SequenceEqual(composition.ServiceSnapshot))
            { throw new HoardLifecycleException([new("StaleComposition", "composition", HoardLifecyclePhase.Validating, Guid.NewGuid())]); }
            composition.Consumed = true;
        }
        var lease = new HoardServiceComposition(composition);
        var coordinator = lease.Coordinator;
        using var cancelled = cancellationToken.Register(() => { _ = coordinator.StopAsync(); });
        try
        {
            foreach (var id in composition.ActivationOrder)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var entry = coordinator.Entries[id];
                var adapter = composition.Adapters.Single(item => item.ProviderType == entry.Registration.ProviderType);
                await coordinator.InvokeStartupAsync(id, HoardLifecyclePhase.Constructing, _ =>
                {
                    entry.Module = (IHoardModule)Activator.CreateInstance(adapter.ModuleType)!;
                    return Task.CompletedTask;
                }).ConfigureAwait(false);
                await coordinator.InvokeStartupAsync(id, HoardLifecyclePhase.ComposingServices, _ =>
                {
                    var before = builder.Services.ToArray();
                    entry.Module!.ConfigureServices(builder.Services);
                    if (builder.Services.Except(before).Any(descriptor => descriptor.ServiceType == typeof(IHostedService)))
                    { throw coordinator.Error("IndependentWorker", id, HoardLifecyclePhase.ComposingServices); }
                    return Task.CompletedTask;
                }).ConfigureAwait(false);
            }
            lock (coordinator.Gate)
            {
                cancellationToken.ThrowIfCancellationRequested();
                coordinator.CheckCanDispatch("composition", HoardLifecyclePhase.ComposingServices);
                builder.Services.AddSingleton<IHoardLifecycle>(coordinator);
                builder.Services.AddSingleton(lease);
                builder.Services.AddSingleton<IHostedService, HoardLifecycleHostedService>();
                return lease;
            }
        }
        catch (Exception error)
        {
            if (error is not HoardLifecycleException)
            { coordinator.Error(error is OperationCanceledException ? "Cancelled" : "PhaseFailure", "composition", coordinator.Snapshot.Phase); }
            await coordinator.StopAsync().ConfigureAwait(false);
            throw new HoardLifecycleException(coordinator.Snapshot.Diagnostics);
        }
    }
}
