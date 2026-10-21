using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
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
        lock (builder.ConfigurationGate)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (builder.Services.Any(d => d.ServiceType == typeof(ConfigurationRegistration)
                && d.ImplementationInstance is ConfigurationRegistration registration
                && composition.Registrations.Any(r => r.ProviderType == registration.ProviderType
                    && composition.EnabledModuleIds.Contains(r.Declaration.Id))))
            { throw new HoardLifecycleException([new("ConfigurationRequired", "composition", HoardLifecyclePhase.Validating, Guid.NewGuid())]); }
            lock (composition)
            {
                if (composition.Consumed || !ReferenceEquals(builder, composition.Builder)
                    || !builder.Services.SequenceEqual(composition.ServiceSnapshot))
                { throw new HoardLifecycleException([new("StaleComposition", "composition", HoardLifecyclePhase.Validating, Guid.NewGuid())]); }
                composition.Consumed = true;
            }
        }
        return await ComposeCoreAsync(builder, new HoardServiceComposition(composition), cancellationToken).ConfigureAwait(false);
    }

    public static async Task<HoardServiceComposition> ComposeHoardModulesAsync(this HoardBuilder builder,
        HoardValidatedConfiguration configuration, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(configuration);
        var consumed = configuration.Consume(builder, cancellationToken);
        return await ComposeCoreAsync(builder, new HoardServiceComposition(consumed.Composition,
            consumed.Options, consumed.Resources), cancellationToken).ConfigureAwait(false);
    }

    private static async Task<HoardServiceComposition> ComposeCoreAsync(HoardBuilder builder,
        HoardServiceComposition lease, CancellationToken cancellationToken)
    {
        var composition = lease.Composition;
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
                    if (entry.Module is IHoardConfiguredModule configured && lease.OwnerOptions.TryGetValue(id, out var options))
                    { configured.ConfigureOptions(options); }
                    lock (coordinator.Gate) { coordinator.CheckCanDispatch(id, HoardLifecyclePhase.ComposingServices); }
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
            lease.ReleaseInputsWhenQuiescent();
            throw new HoardLifecycleException(coordinator.Snapshot.Diagnostics);
        }
    }
}
