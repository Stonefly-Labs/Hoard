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
        HoardValidatedConfiguration? proof = null;
        try
        {
            var data = await ConfigurationEvaluator.RunAsync(builder, input, platformVersions, lifecycleOptions,
                options, supervisor).ConfigureAwait(false);
            supervisor.Complete(true);
            proof = new(data.Composition, data.Owners, supervisor.TransferResources());
        }
        catch (ConfigurationFailure failure) { supervisor.Fail(failure.Rule); }
        if (proof is null) { supervisor.Complete(false); }
        var snapshot = supervisor.Snapshot;
        return new(supervisor.Outcome, new(supervisor.Correlation, snapshot.Diagnostics, snapshot.OmittedCount,
            supervisor.Provenance), supervisor, proof);
    }
}
