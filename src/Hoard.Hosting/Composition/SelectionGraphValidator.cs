using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Composition;

internal static class SelectionGraphValidator
{
    internal static (ImmutableArray<string> Order, ImmutableArray<HoardDependencyEdge> Edges) Validate(
        ImmutableArray<HoardModuleRegistration> registrations, HoardStartupSelection selection,
        HoardPlatformVersions versions, Action<string, string, IEnumerable<string>?> error)
    {
        var registry = registrations.ToDictionary(r => r.Declaration.Id, StringComparer.Ordinal);
        var enabled = selection.EnabledModuleIds.ToHashSet(StringComparer.Ordinal);
        foreach (var id in enabled.Where(id => !registry.ContainsKey(id))) { error("UnknownSelection", id, null); }
        if (enabled.Any(id => !registry.ContainsKey(id))) { return ([], []); }
        foreach (var pair in new[] { (ModuleCategory.Metadata, selection.MetadataModuleId), (ModuleCategory.Artifact, selection.ArtifactModuleId) })
        {
            var candidates = enabled.Where(id => registry[id].Declaration.Category == pair.Item1).ToArray();
            if (candidates.Length != 1 || candidates[0] != pair.Item2) { error("InvalidCardinality", "composition", candidates); }
        }
        var edges = ImmutableArray.CreateBuilder<HoardDependencyEdge>();
        foreach (var id in enabled.Order(StringComparer.Ordinal))
        {
            var declaration = registry[id].Declaration;
            var compatibility = declaration.Compatibility;
            if (!RuntimeCompatibility.Axis(compatibility.HostRange, versions.HostVersion, compatibility.AllowPrereleaseHost)
                || !RuntimeCompatibility.Axis(compatibility.AbstractionsRange, versions.AbstractionsVersion, compatibility.AllowPrereleaseAbstractions))
            { error("UnsupportedPlatform", id, null); }
            foreach (var dependency in declaration.Dependencies)
            {
                if (!enabled.Contains(dependency.ModuleId))
                {
                    if (!dependency.Optional) { error("MissingDependency", id, [id, dependency.ModuleId]); }
                    continue;
                }
                if (!RuntimeCompatibility.Axis(dependency.VersionRange, registry[dependency.ModuleId].Declaration.Version, dependency.AllowPrerelease))
                { error("UnsupportedDependency", id, [id, dependency.ModuleId]); }
                edges.Add(new(dependency.ModuleId, id, dependency.Optional, dependency.VersionRange, dependency.AllowPrerelease));
            }
        }
        foreach (var demand in selection.RequiredCapabilities)
        {
            var capability = enabled.Contains(demand.ModuleId)
                ? registry[demand.ModuleId].Declaration.Capabilities.FirstOrDefault(item => item.Id == demand.CapabilityId) : null;
            if (capability is null || !RuntimeCompatibility.Axis(demand.VersionRange, capability.Version, demand.AllowPrerelease))
            { error("UnsupportedCapability", demand.ModuleId, null); }
        }
        var degree = enabled.ToDictionary(id => id, id => edges.Count(edge => edge.DependentId == id), StringComparer.Ordinal);
        var ready = new SortedSet<string>(degree.Where(pair => pair.Value == 0).Select(pair => pair.Key), StringComparer.Ordinal);
        var order = ImmutableArray.CreateBuilder<string>();
        while (ready.Count > 0)
        {
            var id = ready.Min!;
            ready.Remove(id);
            order.Add(id);
            foreach (var edge in edges.Where(edge => edge.PrerequisiteId == id))
            { if (--degree[edge.DependentId] == 0) { ready.Add(edge.DependentId); } }
        }
        if (order.Count != enabled.Count)
        {
            var remaining = degree.Where(pair => pair.Value > 0).Select(pair => pair.Key).Order(StringComparer.Ordinal).ToArray();
            var path = new List<string>();
            var current = remaining[0];
            while (!path.Contains(current, StringComparer.Ordinal))
            {
                path.Add(current);
                current = edges.Where(edge => edge.DependentId == current && degree[edge.PrerequisiteId] > 0)
                    .Select(edge => edge.PrerequisiteId).Order(StringComparer.Ordinal).First();
            }
            path = path.Skip(path.IndexOf(current)).Append(current).ToList();
            error("DependencyCycle", current, path);
        }
        return (order.ToImmutable(), edges.ToImmutable());
    }
}
