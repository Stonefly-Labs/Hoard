using System.Collections.Immutable;
using Hoard.Abstractions.Modules;
using Hoard.Hosting.Composition;

namespace Hoard.Hosting.Configuration;

internal static class ConfigurationCompositionBridge
{
    internal static HoardValidatedComposition Validate(HoardBuilder builder, EffectiveConfiguration effective,
        HoardPlatformVersions versions, Lifecycle.HoardLifecycleOptions lifecycleOptions,
        HoardConfigurationOptions options, ConfigurationSupervisor supervisor)
    {
        var selection = new HoardStartupSelection
        {
            EnabledModuleIds = [.. effective.Get<string[]>("enabledmodules")],
            MetadataModuleId = effective.Get<string>("metadatamodule"),
            ArtifactModuleId = effective.Get<string>("artifactmodule"),
            RequiredCapabilities = [.. effective.Get<HoardRequiredCapability[]>("requiredcapabilities")]
        };
        var validation = builder.ValidateComposition(selection, versions, lifecycleOptions, options.TimeProvider);
        var composition = validation.Composition;
        if (composition is null)
        {
            supervisor.RejectComposition(validation.Diagnostics, validation.OmittedCount, effective);
        }
        var identities = effective.Get<string[]>("identitymodules").ToImmutableHashSet(StringComparer.Ordinal);
        var expected = composition.Registrations.Where(r => selection.EnabledModuleIds.Contains(r.Declaration.Id)
                && r.Declaration.Category == ModuleCategory.Identity).Select(r => r.Declaration.Id);
        if (!identities.SetEquals(expected))
        {
            supervisor.Reject(HoardConfigurationRule.InvalidSelection, HoardConfigurationPhase.Composition,
                effective.Assignments["identitymodules"].Source, setting: "identitymodules");
        }
        return composition;
    }
}
