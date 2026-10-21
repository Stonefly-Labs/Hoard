using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Configuration;

public static class HoardConfigurationExtensions
{
    public static async Task<HoardConfigurationEvaluation> EvaluateConfigurationAsync(this HoardBuilder builder,
        HoardConfigurationInput input, HoardPlatformVersions platformVersions, HoardLifecycleOptions lifecycleOptions,
        HoardConfigurationOptions? configurationOptions = null, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(platformVersions);
        ArgumentNullException.ThrowIfNull(lifecycleOptions);
        var options = configurationOptions ?? new();
        if (!options.IsValid)
        {
            var id = Guid.NewGuid();
            return new(HoardConfigurationOutcome.Failed, new(id,
                [new(HoardConfigurationRule.InvalidBudget, HoardConfigurationPhase.Sources,
                    HoardConfigurationSource.Defaults, "configuration", "configuration", id)], 0, []));
        }
        var supervisor = new ConfigurationSupervisor(options, cancellationToken);
        EffectiveConfiguration? effective = null;
        try
        {
            if (input.InputError is { } inputError)
            { supervisor.Reject(inputError, HoardConfigurationPhase.Sources, input.InputErrorSource); }
            var metadata = await supervisor.RunAsync(HoardConfigurationPhase.Composition, HoardConfigurationSource.Defaults,
                "configuration", _ => ValueTask.FromResult(ConfigurationMetadata.Validate(builder, options, supervisor))).ConfigureAwait(false);
            effective = await ConfigurationSourceResolution.ResolveAsync(input, metadata, options, supervisor).ConfigureAwait(false);
            supervisor.Reject(HoardConfigurationRule.IncompleteConfiguration, HoardConfigurationPhase.Sources);
        }
        catch (ConfigurationFailure failure) { supervisor.Fail(failure.Rule); }
        supervisor.Complete(false);
        var snapshot = supervisor.Snapshot;
        return new(supervisor.Outcome, new(supervisor.Correlation, snapshot.Diagnostics, snapshot.OmittedCount,
            effective?.Provenance ?? []), supervisor);
    }
}
