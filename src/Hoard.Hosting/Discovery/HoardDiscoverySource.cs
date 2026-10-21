using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Discovery;

internal sealed class HoardDiscoverySource : IHoardDiscoverySource
{
    internal HoardDiscoverySource(HoardServiceComposition lease, DiscoveryRegistration registration)
    { Lease = lease; Registration = registration; }
    internal HoardServiceComposition Lease { get; }
    internal DiscoveryRegistration Registration { get; }

    public HoardDiscoveryReadResult Capture(CancellationToken cancellationToken = default)
    {
        var budget = new DiscoveryReadBudget(Registration.Options, cancellationToken);
        try
        {
            budget.Check();
            var state = Lease.Publication?.Capture();
            if (state is null || state.LifecycleId != Lease.Composition.Identity || Registration.Frozen is not { } catalog)
            { return new("observation-unavailable"); }
            var captured = Registration.Options.TimeProvider.GetUtcNow();
            var modules = DiscoveryInventoryProjector.Project(catalog, Lease.Composition, state, budget);
            modules = DiscoveryCapabilityEvaluator.Project(modules, catalog, Lease.Composition, state,
                Lease.Bindings.Capture(), budget);
            budget.Check();
            return new(new HoardDiscoveryObservation(Registration.Catalog.DistributionId,
                Registration.Catalog.DistributionVersion, Registration.Catalog.InventoryCompleteness,
                state.LifecycleId, state.Revision, captured, state.PublishedAt, state.ReadinessAssessedAt,
                state.Phase, state.Ready, state.StartupAdmission, modules, state.Reasons, state.OmittedReasonCount));
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        { return new("cancelled"); }
        catch (DiscoveryDeadlineException) { return new("deadline"); }
    }
}
