using System.Collections.Immutable;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Configuration;

internal sealed record ConfigurationEvaluationData(HoardValidatedComposition Composition,
    ImmutableDictionary<string, HoardModuleOptions> Owners);

internal static class ConfigurationEvaluator
{
    internal static async Task<ConfigurationEvaluationData> RunAsync(HoardBuilder builder,
        HoardConfigurationInput input, HoardPlatformVersions versions, HoardLifecycleOptions lifecycleOptions,
        HoardConfigurationOptions options, ConfigurationSupervisor supervisor, bool publicOnly = false)
    {
        if (input.InputError is { } inputError)
        { supervisor.Reject(inputError, HoardConfigurationPhase.Sources, input.InputErrorSource); }
        var snapshot = builder.Services.ToImmutableArray();
        var metadata = await supervisor.RunAsync(HoardConfigurationPhase.Composition, HoardConfigurationSource.Defaults,
            "configuration", _ => ValueTask.FromResult(ConfigurationMetadata.Validate(builder, options, supervisor))).ConfigureAwait(false);
        var effective = await ConfigurationSourceResolution.ResolveAsync(input, metadata, options, supervisor).ConfigureAwait(false);
        supervisor.Provenance = effective.Provenance;
        var composition = await supervisor.RunAsync(HoardConfigurationPhase.Composition, HoardConfigurationSource.Defaults,
            "configuration", _ => ValueTask.FromResult(ConfigurationCompositionBridge.Validate(
                builder, effective, versions, lifecycleOptions, options, supervisor))).ConfigureAwait(false);
        var owners = await ConfigurationOptionChecker.CheckAsync(composition, effective, metadata, supervisor).ConfigureAwait(false);
        if (!publicOnly)
        {
            owners = await ConfigurationSecretResolver.ResolveAsync(input, composition, effective, metadata,
                owners, options, supervisor).ConfigureAwait(false);
        }
        if (!builder.Services.SequenceEqual(snapshot) || !snapshot.SequenceEqual(composition.ServiceSnapshot))
        { supervisor.Reject(HoardConfigurationRule.StaleConfiguration, HoardConfigurationPhase.Composition); }
        supervisor.Check();
        return new(composition, owners);
    }
}
