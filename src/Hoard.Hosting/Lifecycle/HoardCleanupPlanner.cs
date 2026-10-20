using System.Collections.Immutable;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Lifecycle;

internal static class HoardCleanupPlanner
{
    internal static bool Unsafe(string id, ImmutableArray<HoardUnsafeActivity> activities, HoardValidatedComposition composition)
    {
        if (activities.Any(activity => activity.ModuleId == "composition" || activity.Kind == HoardActivityKind.Build)) { return true; }
        var protectedIds = activities.Select(activity => activity.ModuleId).ToHashSet(StringComparer.Ordinal);
        bool changed;
        do
        {
            changed = false;
            foreach (var edge in composition.ActiveEdges)
            {
                if (protectedIds.Contains(edge.DependentId)) { changed |= protectedIds.Add(edge.PrerequisiteId); }
            }
        } while (changed);
        return protectedIds.Contains(id);
    }
}
