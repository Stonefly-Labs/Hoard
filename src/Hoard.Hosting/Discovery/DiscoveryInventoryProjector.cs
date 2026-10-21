using System.Collections.Immutable;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Discovery;

internal static class DiscoveryInventoryProjector
{
    internal static ImmutableArray<DiscoveryModule> Project(FrozenDiscovery catalog,
        HoardValidatedComposition composition, DiscoveryPublishedState publication, DiscoveryReadBudget budget)
    {
        var modules = ImmutableArray.CreateBuilder<DiscoveryModule>();
        foreach (var module in catalog.Modules)
        {
            budget.Check();
            var enabled = composition.EnabledModuleIds.Contains(module.Id);
            var state = publication.Modules.SingleOrDefault(item => item.Id == module.Id);
            var readiness = !module.Registered ? "unknown" : !enabled ? "disabled" : publication.Phase switch
            {
                "stopped" => "stopped",
                "stopping" or "draining" or "cleaning-up" => "stopping",
                _ => state?.Readiness ?? "unknown"
            };
            var reasons = module.Reasons.ToBuilder();
            if (!module.Registered) { reasons.Add(new("missing-registration", module.Id)); }
            else if (!enabled) { reasons.Add(new("disabled", module.Id)); }
            var roles = ImmutableArray.CreateBuilder<string>();
            if (enabled && composition.MetadataModuleId == module.Id) { roles.Add("metadata-authority"); }
            if (enabled && composition.ArtifactModuleId == module.Id) { roles.Add("artifact-authority"); }
            if (enabled && module.Category == "identity") { roles.Add("identity-scheme"); }
            modules.Add(module with
            {
                Enabled = enabled,
                LifecyclePhase = module.Registered && !enabled ? "registered" : state?.Phase ?? "unknown",
                Readiness = readiness,
                SelectedRoles = roles.ToImmutable(),
                Reasons = reasons.OrderBy(reason => reason.Code, StringComparer.Ordinal).ToImmutableArray()
            });
        }
        return modules.ToImmutable();
    }
}
