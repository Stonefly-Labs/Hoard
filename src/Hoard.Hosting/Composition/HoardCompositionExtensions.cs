using System.Collections.Immutable;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Composition;

public static class HoardCompositionExtensions
{
    public static HoardCompositionValidation ValidateComposition(this HoardBuilder builder,
        HoardStartupSelection selection, HoardPlatformVersions versions, HoardLifecycleOptions options,
        TimeProvider? timeProvider = null)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(selection);
        ArgumentNullException.ThrowIfNull(versions);
        ArgumentNullException.ThrowIfNull(options);
        var correlation = Guid.NewGuid();
        var errors = new List<HoardLifecycleDiagnostic>();
        var count = 0;
        void Error(string code, string owner, IEnumerable<string>? path = null)
        {
            count++;
            if (errors.Count < 100) { errors.Add(new(code, owner, HoardLifecyclePhase.Validating, correlation, path: path)); }
        }
        var descriptors = builder.Services.ToArray();
        var registrations = descriptors.Where(d => d.ServiceType == typeof(HoardModuleRegistration))
            .Select(d => d.ImplementationInstance as HoardModuleRegistration).ToArray();
        var adapters = descriptors.Where(d => d.ServiceType == typeof(HoardModuleLifecycleRegistration))
            .Select(d => d.ImplementationInstance as HoardModuleLifecycleRegistration).ToArray();
        if (!options.IsValid) { Error("InvalidBudget", "composition"); }
        if (!RuntimeCompatibility.Version(versions.HostVersion, out _) || !RuntimeCompatibility.Version(versions.AbstractionsVersion, out _))
        { Error("UnsupportedPlatform", "composition"); }
        if (selection.EnabledModuleIds.IsDefault || selection.RequiredCapabilities.IsDefault
            || !HoardLifecycleDiagnostic.IsSafeId(selection.MetadataModuleId) || !HoardLifecycleDiagnostic.IsSafeId(selection.ArtifactModuleId)
            || (!selection.EnabledModuleIds.IsDefault && (selection.EnabledModuleIds.Any(id => !HoardLifecycleDiagnostic.IsSafeId(id))
                || selection.EnabledModuleIds.Distinct(StringComparer.Ordinal).Count() != selection.EnabledModuleIds.Length))
            || (!selection.RequiredCapabilities.IsDefault && (selection.RequiredCapabilities.Any(d => d is null
                || !HoardLifecycleDiagnostic.IsSafeId(d.ModuleId) || !HoardLifecycleDiagnostic.IsSafeId(d.CapabilityId)
                || RuntimeCompatibility.Range(d.VersionRange) is null)
                || selection.RequiredCapabilities.Where(d => d is not null).Select(d => (d.ModuleId, d.CapabilityId)).Distinct().Count()
                    != selection.RequiredCapabilities.Length)))
        { Error("InvalidSelection", "composition"); }
        var ids = new HashSet<string>(StringComparer.Ordinal);
        for (var i = 0; i < registrations.Length; i++)
        {
            var registration = registrations[i];
            var safe = HoardLifecycleDiagnostic.IsSafeId(registration?.Declaration?.Id) ? registration!.Declaration.Id : $"registration-{i + 1}";
            if (registration is null || !RegistryValidator.Descriptor(registration.Declaration)
                || !RegistryValidator.Provider(registration.ProviderType, registration.Declaration.Category))
            { Error("MalformedRegistry", safe); }
            if (registration?.Declaration?.Id is { } id && !ids.Add(id)) { Error("DuplicateModule", safe); }
        }
        foreach (var adapter in adapters)
        {
            if (adapter is null || !RegistryValidator.Adapter(adapter.ModuleType)
                || registrations.Count(r => r?.ProviderType == adapter.ProviderType) != 1
                || adapters.Count(a => a?.ProviderType == adapter.ProviderType) != 1)
            { Error("InvalidLifecycleAdapter", "composition"); }
        }
        if (count == 0)
        {
            foreach (var registration in registrations.Where(r => selection.EnabledModuleIds.Contains(r!.Declaration.Id)))
            {
                if (!adapters.Any(a => a!.ProviderType == registration!.ProviderType))
                { Error("MissingLifecycleAdapter", registration!.Declaration.Id); }
            }
        }
        if (count != 0) { return new(null, errors.ToImmutableArray(), count - errors.Count); }
        var registry = registrations.Select(r => r!).ToImmutableArray();
        var associations = adapters.Select(a => a!).ToImmutableArray();
        var graph = SelectionGraphValidator.Validate(registry, selection, versions, Error);
        return count != 0 ? new(null, errors.ToImmutableArray(), count - errors.Count)
            : new(new(builder, selection with { }, versions with { }, options with { }, timeProvider ?? TimeProvider.System,
                registry, associations, graph.Order, graph.Edges), [], 0);
    }
}
