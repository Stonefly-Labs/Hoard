using System.Collections.Immutable;

namespace Hoard.Hosting.Discovery;

internal static class DiscoveryAvailabilityReasons
{
    internal static (ImmutableArray<DiscoveryReason> Reasons, int Omitted) Order(IEnumerable<DiscoveryReason> reasons)
    {
        var ordered = reasons.DistinctBy(reason => (reason.Code, reason.ModuleId, reason.OperationId))
            .OrderBy(reason => reason.Code, StringComparer.Ordinal)
            .ThenBy(reason => reason.ModuleId, StringComparer.Ordinal)
            .ThenBy(reason => reason.OperationId, StringComparer.Ordinal).ToArray();
        return (ordered.Take(100).ToImmutableArray(), Math.Max(0, ordered.Length - 100));
    }
}
