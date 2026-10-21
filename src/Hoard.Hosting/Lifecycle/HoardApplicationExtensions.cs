using Hoard.Hosting.Discovery;
using Hoard.Hosting.Routing;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.DependencyInjection;

namespace Hoard.Hosting.Lifecycle;

public static class HoardApplicationExtensions
{
    public static Task StopHoardApplicationAsync(this WebApplication app,
        HoardServiceComposition serviceComposition, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(app);
        ArgumentNullException.ThrowIfNull(serviceComposition);
        if (!ReferenceEquals(app, serviceComposition.Application))
        { throw serviceComposition.Coordinator.Error("StaleComposition", "composition", HoardLifecyclePhase.Stopping); }
        return serviceComposition.StopApplicationAsync(cancellationToken);
    }

    public static async Task<WebApplication> BuildHoardApplicationAsync(this WebApplicationBuilder builder,
        HoardServiceComposition serviceComposition, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(serviceComposition);
        var coordinator = serviceComposition.Coordinator;
        using var cancelled = cancellationToken.Register(() => { _ = coordinator.StopAsync(); });
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!ReferenceEquals(builder.Services, serviceComposition.Composition.Builder.Services))
            { throw coordinator.Error("StaleComposition", "composition", HoardLifecyclePhase.BuildingHost); }
            await coordinator.InvokeStartupAsync("composition", HoardLifecyclePhase.BuildingHost, async _ =>
            {
                if (serviceComposition.Composition.Builder.DiscoveryRegistration?.Frozen is { } discovery)
                { serviceComposition.Bindings.SealServices(discovery, builder.Services); }
                builder.Services.Insert(0,
                    ServiceDescriptor.Singleton<IStartupFilter>(new HoardModuleAdmissionMiddleware(coordinator)));
                if (serviceComposition.Discovery is not null)
                { builder.Services.Insert(1, ServiceDescriptor.Singleton<IStartupFilter, DiscoveryRawPeerStartupFilter>()); }
                serviceComposition.Application = builder.Build();
                if (serviceComposition.Composition.Builder.DiscoveryRegistration is { } registration)
                { await DiscoveryExposureVerifier.ValidateAsync(builder, serviceComposition.Application, registration.Options).ConfigureAwait(false); }
            }).ConfigureAwait(false);
            lock (coordinator.Gate)
            {
                cancellationToken.ThrowIfCancellationRequested();
                coordinator.CheckCanDispatch("composition", HoardLifecyclePhase.BuildingHost);
                return serviceComposition.Application!;
            }
        }
        catch (Exception error)
        {
            if (error is not HoardLifecycleException)
            { coordinator.Error(error is OperationCanceledException ? "Cancelled" : "PhaseFailure", "composition", HoardLifecyclePhase.BuildingHost); }
            await coordinator.StopAsync().ConfigureAwait(false);
            throw new HoardLifecycleException(coordinator.Snapshot.Diagnostics);
        }
    }

    public static async Task MapHoardModulesAsync(this WebApplication app,
        HoardServiceComposition serviceComposition, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(app);
        ArgumentNullException.ThrowIfNull(serviceComposition);
        var coordinator = serviceComposition.Coordinator;
        using var cancelled = cancellationToken.Register(() => { _ = coordinator.StopAsync(); });
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!ReferenceEquals(app, serviceComposition.Application))
            { throw coordinator.Error("StaleComposition", "composition", HoardLifecyclePhase.ComposingRoutes); }
            var routes = new List<HoardOwnedRoute>();
            foreach (var id in serviceComposition.Composition.ActivationOrder)
            {
                await coordinator.InvokeStartupAsync(id, HoardLifecyclePhase.ComposingRoutes, _ =>
                {
                    var endpoints = new HoardModuleEndpointBuilder(coordinator.Entries[id].Registration.Declaration, coordinator);
                    coordinator.Entries[id].Module!.MapEndpoints(endpoints);
                    routes.AddRange(endpoints.Seal());
                    return Task.CompletedTask;
                }).ConfigureAwait(false);
            }
            await coordinator.InvokeStartupAsync("composition", HoardLifecyclePhase.ComposingRoutes, _ =>
            {
                HoardRouteOwnershipValidator.Validate(app, routes, coordinator);
                return Task.CompletedTask;
            }).ConfigureAwait(false);
            lock (coordinator.Gate)
            {
                coordinator.CheckCanDispatch("composition", HoardLifecyclePhase.ComposingRoutes);
                HoardRouteOwnershipValidator.Publish(app, routes, coordinator);
                if (serviceComposition.Discovery is not null) { serviceComposition.Bindings.SealRoutes(routes); }
                coordinator.VerifyRoutes = () => HoardRouteOwnershipValidator.Validate(app, routes, coordinator);
                coordinator.MarkMapped();
            }
        }
        catch (Exception error)
        {
            if (error is not HoardLifecycleException)
            { coordinator.Error(error is OperationCanceledException ? "Cancelled" : "PhaseFailure", "composition", HoardLifecyclePhase.ComposingRoutes); }
            await coordinator.StopAsync().ConfigureAwait(false);
            throw new HoardLifecycleException(coordinator.Snapshot.Diagnostics);
        }
    }
}
