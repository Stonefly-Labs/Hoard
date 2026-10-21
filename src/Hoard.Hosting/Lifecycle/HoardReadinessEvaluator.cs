using Hoard.Abstractions.Modules;

namespace Hoard.Hosting.Lifecycle;

internal static class HoardReadinessEvaluator
{
    internal static bool Valid(ModuleDescriptor declaration, HoardModuleReadiness? result)
    {
        if (result is null || result.Observations.IsDefault || result.Observations.Length > declaration.Health.Length
            || result.Observations.Any(observation => observation is null || !Enum.IsDefined(observation.Reason)
                || !declaration.Health.Any(health => health.Id == observation.ResponsibilityId))
            || result.Observations.Select(observation => observation.ResponsibilityId).Distinct(StringComparer.Ordinal).Count() != result.Observations.Length)
        { return false; }
        return !result.Ready || declaration.Health.Where(health => health.RequiredForReadiness).All(health =>
            result.Observations.Any(observation => observation.ResponsibilityId == health.Id && observation.Reason == HoardHealthReason.Ready));
    }
}
