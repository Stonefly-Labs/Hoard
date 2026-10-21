using System.Collections.Immutable;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Discovery;

internal static class DiscoveryCapabilityEvaluator
{
    internal static ImmutableArray<DiscoveryModule> Project(ImmutableArray<DiscoveryModule> modules,
        FrozenDiscovery catalog, HoardValidatedComposition composition, DiscoveryPublishedState publication,
        DiscoverySealedBindings bindings, DiscoveryReadBudget budget)
    {
        var byId = modules.ToDictionary(module => module.Id, StringComparer.Ordinal);
        var contributions = new Dictionary<string, List<DiscoveryCapability>>(StringComparer.Ordinal);
        foreach (var contribution in catalog.Contributions)
        {
            budget.Check();
            var reasons = new List<DiscoveryReason>();
            void Reason(string code, string? owner = null) =>
                reasons.Add(new(code, owner is not null && byId.ContainsKey(owner) ? owner : null, contribution.OperationId));
            if (contribution.Support != "supported") { Reason(contribution.Support == "unsupported" ? "unsupported" : "unverified"); }
            if (!bindings.ServicesSealed || !bindings.RoutesSealed
                || contribution.Routes.IsEmpty && contribution.Services.IsEmpty
                || contribution.Routes.Any(route => !bindings.Routes.Contains(route))
                || contribution.Services.Any(service => !bindings.Services.Contains(service)))
            { Reason("binding-unavailable"); }
            var needed = contribution.Owners.Concat(contribution.Dependencies).ToHashSet(StringComparer.Ordinal);
            var pending = new Queue<string>(needed);
            while (pending.TryDequeue(out var dependent))
            {
                budget.Check();
                foreach (var edge in composition.ActiveEdges.Where(edge => !edge.Optional && edge.DependentId == dependent))
                { if (needed.Add(edge.PrerequisiteId)) { pending.Enqueue(edge.PrerequisiteId); } }
            }
            foreach (var owner in needed.Order(StringComparer.Ordinal))
            {
                budget.Check();
                if (!byId.TryGetValue(owner, out var module) || !module.Registered || !module.Enabled)
                { Reason("dependency-unavailable", owner); continue; }
                if (module.Readiness != "ready")
                {
                    Reason(module.Readiness switch
                    {
                        "initializing" or "enabled" => "initializing",
                        "not-ready" or "failed" => "not-ready",
                        "stopping" => "stopping",
                        "stopped" => "stopped",
                        _ => "observation-unknown"
                    }, owner);
                }
            }
            if (publication.Phase == "stopped") { Reason("stopped"); }
            else if (publication.Phase is "stopping" or "draining" or "cleaning-up") { Reason("stopping"); }
            else if (publication.Phase != "running" || !publication.StartupAdmission) { Reason("initializing"); }
            var ordered = DiscoveryAvailabilityReasons.Order(reasons);
            var availability = reasons.Count == 0 ? "usable"
                : reasons.All(reason => reason.Code is "unverified" or "observation-unknown") ? "unknown" : "unavailable";
            var capability = new DiscoveryCapability(contribution.CapabilityId, contribution.Version, contribution.OperationId,
                contribution.Owners, contribution.Dependencies.Where(byId.ContainsKey).ToImmutableArray(),
                contribution.Support, contribution.EvidenceScope, contribution.EvidenceIds, availability, ordered.Reasons, ordered.Omitted);
            if (!contributions.TryGetValue(contribution.Owners[0], out var owned))
            { contributions.Add(contribution.Owners[0], owned = []); }
            owned.Add(capability);
        }
        return modules.Select(module => contributions.TryGetValue(module.Id, out var owned)
            ? module with { Capabilities = owned.ToImmutableArray() } : module).ToImmutableArray();
    }
}
